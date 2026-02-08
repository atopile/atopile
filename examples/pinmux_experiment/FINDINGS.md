# Pin Mux in atopile — Experiment Findings & Architecture Proposal

## Problem Statement

Current STM32 (and other MCU) definitions expose ALL peripheral instances with hardcoded pin assignments:
```ato
uart = new UART[10]    # 10 UARTs, all wired
spi = new SPI[5]       # 5 SPIs, all wired  
i2c = new I2C[5]       # 5 I2Cs, all wired
```

Problems:
1. **No conflict detection**: Using I2C1 and SPI3 might share PA5, but nothing catches it
2. **No auto-assignment**: User can't say "give me an I2C" — they must know which instance and pins
3. **Wasted netlist**: All peripheral-to-pin connections exist even if unused
4. **No alt-pin support**: Each peripheral is wired to ONE pin set, but most have 2-4 alternate mappings

## Research Summary

### Zephyr (Linux devicetree pinctrl)
- **State-based model**: Each device has named pin configurations (`default`, `sleep`)
- **Static declarations**: Pin mux is declared in devicetree overlays, not auto-assigned
- **Vendor macros**: `STM32_PINMUX('A', 5, AF5, ...)` encodes valid mux options
- **No solver**: Assignment is manual; the build system validates but doesn't search

### STM32CubeMX
- **Constraint solver**: Auto-assigns pins when peripherals are enabled
- **Conflict detection**: Shows which peripherals conflict in real-time
- **Alternate pin search**: Can shift assignments to resolve conflicts
- **Algorithm**: Likely a greedy search with backtracking (not SAT/CSP)

### Rust Embedded HALs
- **Type-state pattern**: Pin states encoded in the type system
- **Compile-time checking**: Invalid mux = compile error
- **Zero-cost**: No runtime overhead, but macro-heavy implementation
- **No auto-assignment**: User explicitly calls `into_alternate_af5()`

## Experiment Results

### Exp 1-4: Structural approaches (all build OK)
- Arrays of I2C/SPI work fine structurally
- User can connect to `mcu.i2c[0]` or `mcu.i2c1_config_a` explicitly
- **No conflict detection**: Connecting two peripherals to the same GPIO merges nets silently

### Exp 5: Conflict via shared GPIO (builds OK — BAD)
- Connected I2C SCL and UART TX to same GPIO pin
- **Build succeeds** — atopile just merges the nets
- No mechanism to detect that one physical pin can't be both I2C and UART

### Exp 7: Solver contradiction detection
- `assert r.resistance within 1kohm +/- 1%` AND `assert r.resistance within 10kohm +/- 1%`
- **Build FAILS with "Contradiction: Empty superset"** — solver catches it
- But ONLY because the resistor needs part picking, which triggers solver resolution

### Exp 8: Unlinked parameters (builds OK — BAD)
- `assert function_id within 1 to 1` AND `assert function_id within 3 to 3`
- **Build succeeds** — the solver never evaluates `function_id`
- Free-standing dimensionless parameters are not in the solver's resolution path

### Exp 9: Linked parameters (builds FAILS — GOOD)
- Made `function_id` feed into a resistor expression: `assert phantom.resistance within function_id * 1kohm +/- 10%`
- **Build FAILS with "Contradiction: Deduced predicate to false 1 ⊆!∅ 3"**
- The solver catches the contradiction when the parameter is in the dependency chain

## Key Findings

1. **The solver CAN detect contradictions** — but only on parameters that are in the resolution path (connected to something that needs solving, like part picking)

2. **The solver CANNOT auto-assign** — it does constraint propagation and validation, not combinatorial search. It can't solve "pick one of {PB6, PB8, PF1} for I2C1_SCL"

3. **Connections are structural, not conditional** — `a ~ b` always creates a net. There's no "connect if condition" or "connect one of {a, b, c}"

4. **No mechanism for mutual exclusion on nets** — connecting two peripherals to the same ElectricLogic is valid (net merge), with no way to say "this pin can only serve one function at a time"

## The Addressor Pattern — Precedent for Solver-Driven Pin Mux

The existing `Addressor` module (`src/faebryk/library/Addressor.py`) already implements
exactly the pattern needed for pin mux:

```
[Parameters]  →  [Solver resolves]  →  [Post-solve check makes connections]
```

### How Addressor works:
1. `offset` parameter is numeric, range [0, 2^N - 1]
2. `address = base + offset` — an `Is` expression links them
3. User constrains the address: `assert addressor.address is i2c.address`
4. When two devices share an I2C bus, the solver forces their addresses to differ
5. **Post-solve design check** (`@register_post_instantiation_setup_check`) reads the
   resolved `offset` and physically connects each address pin to hv or lv

The `SinglePinAddressor` extends this: it has N `states` (Electrical destinations),
and the post-solve check connects `address_line` to `states[offset]`.

### Applying the Addressor pattern to Pin Mux:

A `PinMuxSelector` would work identically:

```python
class PinMuxSelector(fabll.Node):
    """Selects one of N pin configurations for a peripheral."""
    selection = NumericParameter(range=[0, N-1])  # solver resolves this
    
    # N possible configurations, each an interface (e.g., I2C with specific pins)
    configs = [I2C_PinConfig for _ in range(N)]
    
    # The external-facing interface
    peripheral = I2C
    
    @post_solve_check
    def connect_selected_config(self):
        idx = int(solver.resolve(self.selection))
        # Connect the selected config's pins to the GPIO array
        self.configs[idx].activate()
```

## Proposed Architecture

### Phase 1: PinMuxSelector Module (Addressor-style, solver-driven)

Build a `PinMuxSelector<configs=N>` module following the Addressor pattern exactly:

```ato
module ST_STM32F407_I2C1_Mux:
    """I2C1 can live on PB6/PB7 OR PB8/PB9"""
    
    selector = new PinMuxSelector<configs=2>
    
    # Config 0: PB6/PB7
    selector.configs[0].scl ~ gpio_b[6]
    selector.configs[0].sda ~ gpio_b[7]
    
    # Config 1: PB8/PB9
    selector.configs[1].scl ~ gpio_b[8]
    selector.configs[1].sda ~ gpio_b[9]
    
    # External interface — the solver picks which config
    i2c1 = new I2C
    i2c1 ~ selector.peripheral
```

**How it resolves**: The `selection` parameter starts unconstrained [0, N-1].
When the user connects `sensor.i2c ~ mcu.i2c1`, the solver narrows `selection`
based on which GPIO pins are still available. If PB6 is already used by UART1,
the solver eliminates config 0 and `selection` resolves to 1 (PB8/PB9).

**Conflict detection**: If ALL configs are eliminated (all pin options conflict),
the solver produces a contradiction — just like the Addressor when an I2C address
is impossible.

**Key constraint mechanism**: Each GPIO pin gets a `function_id` parameter.
When a PinMuxSelector activates a config, it constrains the relevant pins'
`function_id` values. Two selectors trying to use the same pin will create
contradictory constraints on that pin's `function_id`, caught by the solver.

### Phase 2: "Give me any I2C" UX

With PinMuxSelectors in place, the user experience becomes:

```ato
module MyBoard:
    mcu = new STM32H723
    sensor = new BME280
    
    # Connect to the MCU's I2C mux — solver picks pins
    sensor.i2c ~ mcu.i2c_mux.peripheral
    
    # Or explicitly pick I2C1 on config B
    sensor.i2c ~ mcu.i2c1_mux.peripheral
    assert mcu.i2c1_mux.selection within 1 to 1
```

The first form ("give me any I2C") requires one more abstraction — a `PeripheralPool`
that holds multiple `PinMuxSelector`s and assigns the first available one:

```ato
module I2C_Pool:
    """Pool of I2C peripherals with automatic assignment."""
    mux = new PinMuxSelector[5]  # 5 I2C instances
    
    # A "request" interface — connecting to it claims one from the pool
    # The pool_index parameter determines which one
    pool_index: dimensionless
    assert pool_index within 0 to 4
```

This is where the solver extension gets interesting — the `pool_index` would need
to be constrained by mutual exclusion (no two users can claim the same index).
The Addressor already handles this for I2C addresses on a shared bus, so the
pattern is proven.

### Phase 3: Auto-generator integration

The STM32 generator would produce `PinMuxSelector` instances instead of hardcoded
pin assignments:

```python
# In stm32_gen.py, instead of:
#   i2c[0].scl ~ gpio_b[6]
#   i2c[0].sda ~ gpio_b[7]
# Generate:
#   i2c1_mux = new PinMuxSelector<configs=3>
#   i2c1_mux.configs[0].scl ~ gpio_b[6]    # AF4
#   i2c1_mux.configs[0].sda ~ gpio_b[7]    # AF4
#   i2c1_mux.configs[1].scl ~ gpio_b[8]    # AF4
#   i2c1_mux.configs[1].sda ~ gpio_b[9]    # AF4
#   i2c1_mux.configs[2].scl ~ gpio_h[7]    # AF4  (if available)
#   i2c1_mux.configs[2].sda ~ gpio_h[8]    # AF4
```

The XML data already has all alternate function mappings. The generator just
needs to enumerate valid pin combinations per peripheral instance.

## Implementation Roadmap

1. **Build `PinMuxSelector`** as a Python library module following the Addressor pattern
   - `selection` NumericParameter with [0, N-1] range
   - N interface children (configs)
   - 1 external-facing interface (peripheral)
   - Post-solve check that activates the selected config

2. **Build `PinSlot`** — a GPIO pin wrapper with a `function_id` parameter
   - When a PinMuxSelector activates, it constrains `function_id` on its pins
   - Mutual exclusion: two selectors on the same pin = contradictory `function_id`

3. **Test with a minimal MCU** — 2 I2C instances, 2 configs each, verify:
   - Solver resolves selection when only one config is valid
   - Contradiction when all configs conflict
   - User can override with `assert selection within X to X`

4. **Integrate with STM32 generator** — generate PinMuxSelector-based modules

5. **Build PeripheralPool** for "give me any I2C" abstraction

## Open Questions

1. **Post-solve connection timing**: The Addressor makes connections in
   `POST_INSTANTIATION_SETUP`. Pin mux connections need to happen before
   part picking (since they affect the netlist). Is this timing correct?

2. **Scale**: An H7 has ~10 UARTs × 3 configs each = 30 pin-config combinations.
   Does the solver handle this many inter-dependent parameters efficiently?

3. **Unconnected peripherals**: If the user doesn't use I2C3, its PinMuxSelector
   should be "inactive" (selection unconstrained, no pins claimed). Need to
   ensure inactive selectors don't interfere.

4. **Mixed explicit/auto**: User explicitly picks I2C1 on PB8/PB9, then asks
   for "any UART" — the auto-assigned UART must avoid PB8/PB9. This requires
   the explicit selection to constrain the pin `function_id`s before the
   auto-assignment runs.
