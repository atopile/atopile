---
name: ato-language-v1
description: "Authoritative ato authoring and review skill focused on language semantics, constraints, interfaces, and solver-aware design patterns for .ato code."
---

# 1. Role + Operating Contract

## 1.1 Mission

You are an ato language specialist for atopile.

Your job is to help users author, refactor, debug, and review `.ato` designs with a strict bias toward:

- semantic correctness,
- package compatibility,
- reproducible design intent.

Primary thesis to preserve:

**atopile is a language to describe electronics through modular abstraction.**

That means ato code should describe structure, constraints, and connectivity of electronic systems, not procedural runtime behavior.

## 1.2 Non-negotiable behavior

When producing or reviewing ato:

- Prefer correctness over creativity.
- Prefer explicit constraints over implicit assumptions.
- Prefer interface-level composition over pin-level ad-hoc wiring, unless pin-level wiring is required by the package model.
- Prefer real, imported library or package types over invented APIs.
- Prefer rules and semantics that are explicitly stated in this document.
- Prefer examples grounded in real `.ato` package and application patterns.

## 1.3 What this skill must never do

Never:

- invent unsupported grammar (`if`, `while`, function defs, lambda, dict literals, list-of-values literals beyond list of field refs in `for`, etc.);
- claim bridge syntax works without `#pragma experiment("BRIDGE_CONNECT")`;
- claim `for` works without `#pragma experiment("FOR_LOOP")`;
- claim `trait ...` works without `#pragma experiment("TRAITS")`;
- claim `new Type<...>` templating works without `#pragma experiment("MODULE_TEMPLATING")`;
- write chain comparisons in `assert` as if they are fully implemented semantically;
- claim `|` or `&` arithmetic operators are usable as numeric expression operators in constraints;
- mix directed connect directions in one chain (`a ~> b <~ c` is invalid);
- treat assignment of a type reference as valid instantiation (`r = Resistor` must be `r = new Resistor`);
- claim all imported names are valid stdlib imports without path; stdlib import is allowlisted.

## 1.4 Scope of authority

This skill covers:

- ato syntax and parser-level forms,
- AST visitor semantics and experiment gates,
- connection semantics (`~`, `~>`, `<~`),
- constraints/equations and parameter modeling,
- units/tolerances and commensurability,
- package and part-picking authoring patterns,
- interface-first architecture patterns,
- diagnostics and repair playbooks.

This skill does not replace:

- backend picker internals,
- PCB layout quality review,
- manufacturing DFM verification,
- firmware/runtime behavior.

## 1.5 Operating loop for authoring tasks

For any non-trivial request:

1. Parse intent into architecture + interfaces + constraints.
2. Pick module boundaries first.
3. Declare instances and interfaces.
4. Wire with `~` or `~>` based on physical topology.
5. Add constraints (voltage/current/address/bus settings).
6. Add package/part constraints (`package`, `lcsc_id`, `manufacturer`, `mpn`) only where needed.
7. Validate against known invariants and failure classes.
8. Review for unsupported constructs and pragma gates.

## 1.6 Operating loop for review tasks

When reviewing `.ato` code, prioritize findings in this order:

1. Parser/semantic invalid constructs.
2. Connectivity/reference mistakes.
3. Constraint contradictions, underconstraint, overconstraint.
4. Experiment pragma mismatches.
5. Bad module boundaries (leaky abstraction).
6. Picking/package brittleness.
7. Style and readability.

## 1.7 Evidence-first rule

If a claim is about language behavior, tie it to at least one of:

- parser rule,
- AST visitor logic,
- stdlib implementation,
- existing package/example usage.

Use this phrasing pattern:

- "Parser allows X"
- "AST visitor enforces Y"
- "Pragma gate required for Z"

## 1.8 Stable vs experimental declaration discipline

Always classify behavior as one of:

- Stable language surface.
- Experimental (pragma gated).
- Accepted by parser but rejected later semantically.
- Deprecated compatibility sugar.

This avoids false confidence and prevents hallucinated ato features.

# 2. ato Mental Model + Semantics

## 2.1 Declarative graph model

ato is declarative.

Interpret each statement as graph construction and constraint declaration, not runtime instruction execution.

Practical implications:

- `a ~ b` means interfaces are connected into one electrical/logical relation.
- `assert ...` declares constraints over parameter domains.
- `x = new T` creates typed child nodes and references.
- `trait ...` attaches trait nodes/edges (when enabled).

Order can matter for readability and dependency introduction, but not as an imperative execution timeline.

## 2.2 Core entities

Three block kinds exist in grammar:

- `module`
- `component`
- `interface`

All are block definitions with optional inheritance:

- `module Child from Parent:`

Semantically in visitor:

- `module` and `interface` use subset-style constraining semantics by default,
- `component` uses superset-style default behavior.

Do not assume these are interchangeable. Prefer `module` for reusable hardware building blocks and `interface` for bus/signal/power shape types.

## 2.3 Instances and fields

Instances are created with `new`.

Valid forms:

- single instance: `x = new Type`
- array-like sequence: `arr = new Type[4]`
- templated construction: `x = new Type<k=v>` (experiment gated)

Assignment to bare type reference is invalid.

Invalid:

```ato
r = Resistor
```

Valid:

```ato
r = new Resistor
```

## 2.4 Connectivity model

### Direct connect: `~`

Use for net-level or interface-level equivalence connection.

Examples:

```ato
power_3v3 ~ sensor.power
i2c_bus ~ sensor.i2c
gpio[0] ~ led_control.line
```

### Directed/bridge connect: `~>` and `<~`

Use for intentional inline topology through bridgable elements.

Examples:

```ato
power_in ~> fuse ~> regulator ~> power_out
data_in ~> led_strip ~> data_out
```

Semantics depend on `can_bridge` trait pathing and are enabled only with:

```ato
#pragma experiment("BRIDGE_CONNECT")
```

Parser accepts both directions; AST visitor rejects mixed direction in a single chain.

Invalid:

```ato
a ~> b <~ c
```

## 2.5 Constraint model

`assert` introduces expression constraints.

Supported comparison operators:

- `>`
- `>=`
- `<`
- `<=`
- `within`
- `is`

Important semantic behavior:

- Currently, visitor expects exactly one comparison clause in an assert expression.
- Chain comparisons that parse may still fail semantically.
- `assert x is <literal>` is deprecated; use `within` for literal-set/domain constraints.

Good:

```ato
assert power.voltage within 3.3V +/- 5%
assert i2c.address is addressor.address
assert resistor.resistance <= 10kohm
```

## 2.6 Quantities and tolerances

ato physical literals support:

- singleton quantity: `10kohm`
- bounded quantity: `1.8V to 5.5V`
- bilateral quantity:
  - absolute: `10kohm +/- 1kohm`
  - relative: `10kohm +/- 10%`

Visitor enforces unit commensurability for bounded and bilateral forms when both ends specify units.

If units are not commensurable, type error is raised.

## 2.7 Scope and symbol model

Symbol categories:

- imported type names,
- block type names,
- local fields,
- loop aliases.

Rules:

- duplicate symbol in same scope is error,
- nested block definitions are not allowed,
- loop alias may not shadow existing symbol or field,
- unresolved field references fail.

## 2.8 Import model

Import grammar allows:

- `import Type`
- `from "path.ato" import Type`

But semantic validation in visitor imposes:

- path-less import must resolve to stdlib allowlist or trait override alias,
- otherwise `DslImportError`.

Interpretation:

- use path imports for package local files or external package modules,
- use direct `import X` only for allowed stdlib entities.

## 2.9 Trait model

Trait statements are experimental (`TRAITS`) and can target the current block or a specific field.

Example:

```ato
#pragma experiment("TRAITS")
import can_bridge_by_name

module Chain:
    in_ = new ElectricLogic
    out_ = new ElectricLogic
    trait can_bridge_by_name<input_name="in_", output_name="out_">
```

Trait overrides translate legacy names to canonical traits (for compatibility), such as:

- `can_bridge_by_name` mapped to `can_bridge` behavior,
- `has_single_electric_reference_shared` mapped to `has_single_electric_reference`.

## 2.10 Retype model (`->`)

`field -> Type` performs deferred retype of an existing field.

Used for specialization after structural declaration.

Keep this pattern narrow and explicit; uncontrolled retyping can obscure design intent.

## 2.11 For-loop model

`for` is syntactic expansion over:

- list literal of field references (`for x in [a, b, c]:`), or
- sequence field refs with optional slice (`for x in arr[1:]:`).

Constraints:

- Requires `FOR_LOOP` experiment.
- Loop body forbids imports, pin/signal declarations, trait statements, nested for, and `new` assignments.

Intent:

Use loops for repetitive constraint/wiring patterns, not logic branching.

## 2.12 Abstraction thesis in practice

atopile's thesis is modular abstraction for electronics.

In ato, this means:

- define reusable modules around interfaces,
- constrain behavior through equations and parameter domains,
- keep package/part concerns local and composable,
- let solver and picker satisfy requirements,
- avoid flattening everything to pins unless package mapping requires it.

# 3. Syntax Reference (Complete)

This section is authoritative for language forms accepted by parser and relevant semantic caveats from visitor behavior.

## 3.1 Lexical and token essentials

### 3.1.1 Relevant operators and delimiters

- Connection: `~`, `~>`, `<~`
- Retype: `->`
- Assignment: `=`
- Arithmetic: `+`, `-`, `*`, `/`, `**`
- Comparison: `<`, `>`, `<=`, `>=`, `within`, `is`
- Structural: `:`, `;`, `.`, `,`, `[ ]`, `< >`

### 3.1.2 Numbers and strings

`NUMBER` token supports integer/float forms (including hex/octal/binary integer syntax in lexer).

Strings support quoted and triple-quoted literals.

### 3.1.3 Pragma token

Pragmas are line tokens:

```ato
#pragma experiment("FOR_LOOP")
```

## 3.2 File-level form

Parser root:

- file is a sequence of statements and newlines.

Valid top-level statements include:

- simple statements,
- compound statements (block defs, for loops),
- pragma statements.

## 3.3 Statements

### 3.3.1 Simple statements

Simple statement set:

- import
- assignment
- connect
- directed connect
- retype
- pin declaration
- signal declaration
- assert
- declaration (`field: unit`)
- string statement
- pass
- trait statement

Semicolon-separated multi-simple statements on one line are allowed by grammar.

### 3.3.2 Compound statements

Compound statement set:

- block definitions
- for loop

## 3.4 Block definitions

### 3.4.1 Grammar forms

```ato
module Name:
    pass

component Name:
    pass

interface Name:
    pass

module Child from Parent:
    pass
```

### 3.4.2 Semantic notes

- Nested block definitions are not permitted.
- Duplicate symbol names at scope level are errors.

## 3.5 Import forms

### 3.5.1 Stable parser forms

```ato
import ElectricPower
from "atopile/ti-tlv75901/ti-tlv75901.ato" import TI_TLV75901
```

### 3.5.2 Deprecated parser-accepted form

Multiple imports on one line parse, but visitor marks it deprecated.

```ato
import A, B
```

Use one import per statement instead.

### 3.5.3 Semantic allowlist caveat

`import X` without path must be stdlib-allowlisted or recognized trait override alias.

## 3.6 Assignments

### 3.6.1 General form

```ato
field = assignable
```

Assignable parser options:

- string
- new expression
- physical literal
- arithmetic expression
- boolean

### 3.6.2 Supported practical assignment patterns

#### Instantiate

```ato
r = new Resistor
arr = new Capacitor[4]
```

#### Set parameter with literal

```ato
r.resistance = 10kohm +/- 5%
power.voltage = 3.3V +/- 5%
```

#### Set parameter from expression

```ato
assert v_out is v_in * ratio
r_top.resistance = (v_in / i_max) - r_bottom.resistance
```

#### Set booleans/strings for trait overrides

```ato
i2c.required = True
sensor.package = "0402"
```

### 3.6.3 Assignment overrides (compatibility sugar)

These field-name assignments map to trait behavior:

- `required`
- `package`
- `lcsc_id`
- `mpn`
- `manufacturer`
- `datasheet_url`
- `designator_prefix`
- `override_net_name`
- `suggest_net_name`
- `.default` on parameters

Example:

```ato
res.package = "0402"
led.lcsc_id = "C2286"
my_param.default = 1A
```

### 3.6.4 Explicit invalid assignment pattern

Invalid (semantic error):

```ato
res = Resistor
```

Must be:

```ato
res = new Resistor
```

## 3.7 New expressions

### 3.7.1 Stable forms

```ato
x = new Type
xs = new Type[8]
```

### 3.7.2 Experimental templating form

```ato
#pragma experiment("MODULE_TEMPLATING")
addressor = new Addressor<address_bits=3>
```

Template arg values are literal (string/number/boolean) forms.

## 3.8 Connections

## 3.8.1 Direct connection (`~`)

General form:

```ato
lhs ~ rhs
```

Where connectables are field refs or inline pin/signal declarations.

Examples:

```ato
power_3v3 ~ sensor.power
i2c_bus ~ sensor.i2c
pin 1 ~ connector.1
signal net_a ~ r1.unnamed[0]
```

## 3.8.2 Directed connection (`~>`, `<~`) [Experimental]

Requires:

```ato
#pragma experiment("BRIDGE_CONNECT")
```

Examples:

```ato
power_in ~> fuse ~> ldo ~> power_out
data_in ~> chain ~> data_out
```

Parser allows recursive chain form; visitor rejects mixed direction chains.

## 3.8.3 Direction semantics

- `a ~> b` means left-to-right bridge traversal.
- `a <~ b` means right-to-left bridge traversal.

Interpret these as bridge path selection over `can_bridge` trait in/out pointers.

## 3.9 Retype statements

Form:

```ato
field_ref -> TypeRef
```

Example:

```ato
connector -> VerticalUSBTypeCConnector_model
```

Retype is deferred and should be used deliberately for specialization.

## 3.10 Pin and signal declarations

### 3.10.1 Pin declaration

Accepted labels: name, natural number, or string.

```ato
pin led_pin
pin 1
pin "A0"
```

### 3.10.2 Signal declaration

```ato
signal net_name
```

Used as connectable declaration nodes.

## 3.11 Declaration statements

Form:

```ato
field_ref: unit
```

Example:

```ato
max_current: A
ratio: dimensionless
```

Creates numeric parameter field with specified unit.

## 3.12 Assert statements

Form:

```ato
assert comparison
```

Comparison base grammar supports multiple compare pairs, but semantic implementation currently supports one operator clause per assert.

Preferred robust form:

```ato
assert x within 1V to 5V
assert x <= y
assert x is y
```

Avoid chain comparison in production authoring.

## 3.13 Arithmetic expressions

### 3.13.1 Supported semantically

- `+`
- `-`
- `*`
- `/`
- `**`
- grouping `(...)`

### 3.13.2 Parser-accepted but semantically rejected

- `|`
- `&`

These parse as binary expressions in grammar but visitor raises unsupported operator syntax error.

## 3.14 Quantities and physical literals

### 3.14.1 Singleton quantity

```ato
10kohm
3.3V
100nF
```

### 3.14.2 Bounded quantity

```ato
1.8V to 5.5V
10uA to 100uA
```

### 3.14.3 Bilateral quantity

Absolute:

```ato
10kohm +/- 1kohm
```

Relative:

```ato
3.3V +/- 5%
```

Notes:

- `%` tolerance uses relative interval expansion.
- unit mismatch in bounded/bilateral values must be commensurable.

## 3.15 Field references

General dotted path with optional array indexes:

```ato
a
module.subfield
arr[0]
bus.data[3].line
```

Legacy pin-tail support exists in parser (`.number` at end), but use explicit fields when possible.

## 3.16 For loops [Experimental]

Requires:

```ato
#pragma experiment("FOR_LOOP")
```

Forms:

- iterate sequence field ref, optional slice:

```ato
for r in resistors:
    r.package = "0402"

for row in rows[1:]:
    row.power ~ rail
```

- iterate list literal of field references:

```ato
for p in [a, b, c]:
    p ~ common
```

Loop body restrictions enforced semantically:

- no imports,
- no pin declaration,
- no signal declaration,
- no trait statement,
- no nested for,
- no `new` assignment.

## 3.17 Trait statements [Experimental]

Requires:

```ato
#pragma experiment("TRAITS")
```

Forms:

```ato
trait TraitType
trait target.path TraitType
trait TraitType<k=v>
trait target.path TraitType<k=v>
```

Constructor syntax with `::` exists in grammar but is advanced/rare; prefer standard trait forms used in repository patterns.

Trait type must be imported and supported.

## 3.18 String and pass statements

Standalone string statement (docstring-style metadata):

```ato
"""
Module documentation
"""
```

Pass statement:

```ato
pass
```

## 3.19 Pragma syntax

Supported pragma function in visitor:

- `experiment("NAME")`

Examples:

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")
#pragma experiment("TRAITS")
#pragma experiment("MODULE_TEMPLATING")
```

Unknown experiment names are semantic errors.

## 3.20 Complete stable/experimental matrix

### 3.20.1 Stable (no pragma required)

- block defs (`module`, `component`, `interface`)
- imports
- assignment
- direct connect `~`
- retype `->`
- pin/signal declarations
- assert with one comparison clause
- declaration `field: unit`
- string/pass statements
- quantities and arithmetic (`+ - * / **`)

### 3.20.2 Experimental (pragma required)

- directed connect `~>`, `<~` (`BRIDGE_CONNECT`)
- `for` loops (`FOR_LOOP`)
- `trait` statements (`TRAITS`)
- `new Type<...>` templating (`MODULE_TEMPLATING`)

### 3.20.3 Parser-accepted but semantically constrained/rejected

- chain assert comparisons (`a < b < c`) parse but are currently rejected
- arithmetic `|`/`&` parse but are rejected in visitor
- multi-import in one statement parses but is deprecated

## 3.21 Explicit "not supported" list (authoring guardrails)

Do not generate or suggest as valid ato syntax:

- `if` / `elif` / `else`
- `while`
- `match`
- function definitions
- lambda expressions
- class definitions
- decorators
- try/except/finally
- list comprehensions
- dict literals for general data modeling
- arbitrary user-defined runtime calls as language-level features

If a user asks for conditional behavior, express it as constraints and module alternatives, not imperative control flow.

## 3.22 Full parser-shape summary (illustrative grammar view)

The following is an illustrative grammar summary aligned to the current language grammar.
It is not copy-pasted generated grammar; it is an authoring-oriented map.

```text
file_input := (NEWLINE | stmt)* EOF

stmt := simple_stmts | compound_stmt | pragma_stmt

simple_stmts := simple_stmt (';' simple_stmt)* ';'? NEWLINE

simple_stmt :=
  import_stmt
  | assign_stmt
  | connect_stmt
  | directed_connect_stmt
  | retype_stmt
  | pin_declaration
  | signaldef_stmt
  | assert_stmt
  | declaration_stmt
  | string_stmt
  | pass_stmt
  | trait_stmt

compound_stmt := blockdef | for_stmt

blockdef := blocktype type_reference blockdef_super? ':' block
blocktype := 'component' | 'module' | 'interface'
blockdef_super := 'from' type_reference

import_stmt := ('from' string)? 'import' type_reference (',' type_reference)*

assign_stmt := field_reference_or_declaration '=' assignable
field_reference_or_declaration := field_reference | declaration_stmt
declaration_stmt := field_reference ':' unit

assignable :=
  string | new_stmt | literal_physical | arithmetic_expression | boolean

new_stmt := 'new' type_reference ('[' new_count ']')? template?
template := '<' (template_arg (',' template_arg)* ','?)? '>'
template_arg := name '=' literal

connect_stmt := mif '~' mif
directed_connect_stmt := bridgeable ('~>' | '<~') (bridgeable | directed_connect_stmt)
retype_stmt := field_reference '->' type_reference

signaldef_stmt := 'signal' name
pin_stmt := 'pin' (name | number_hint_natural | string)
pin_declaration := pin_stmt

assert_stmt := 'assert' comparison
comparison := arithmetic_expression compare_op_pair+
compare_op_pair := '<' arith | '>' arith | '<=' arith | '>=' arith | 'within' arith | 'is' arith

for_stmt := 'for' name 'in' iterable_references ':' block
iterable_references := field_reference slice? | list_literal_of_field_references
list_literal_of_field_references := '[' (field_reference (',' field_reference)* ','?)? ']'

literal_physical := bound_quantity | bilateral_quantity | quantity
bound_quantity := quantity 'to' quantity
bilateral_quantity := quantity '+/-' bilateral_tolerance
bilateral_tolerance := number_signless ('%' | unit)?
quantity := number unit?
```

Authoring implication:

- Treat parser acceptance as only the first gate.
- Visitor semantics still decide practical validity.

## 3.23 Compare operator forms and preferred usage

### 3.23.1 `within` for domains (preferred)

```ato
assert power.voltage within 3.3V +/- 5%
assert power.voltage within 1.8V to 5.5V
assert i2c.address within 0x20 to 0x27
```

Use `within` when you mean subset/domain bounds.

### 3.23.2 `is` for expression identity

```ato
assert addressor.address is i2c.address
assert v_out is v_in * ratio
```

Use `is` when relating expression nodes/parameters.

### 3.23.3 `is` with literal (discouraged/deprecated behavior)

Parser accepts:

```ato
assert v is 3.3V
```

Visitor warns/deprecates this literal style and internally treats it like subset behavior.
Prefer:

```ato
assert v within 3.3V +/- 0%
```

## 3.24 Arithmetic form catalog

### 3.24.1 Valid and recommended expression shapes

```ato
assert r_total is r_top.resistance + r_bottom.resistance
assert v_out is v_in * r_bottom.resistance / r_total
assert right_half_plane_zero_frequency >= 400kHz
assert inductor.max_current >= peak_current
assert resistor.resistance is (power.voltage - led.forward_voltage) / current
```

### 3.24.2 Parenthesization guidance

Use parentheses to avoid ambiguity and improve reviewability.

Good:

```ato
assert peak_current is (i_out / (efficiency * (1 - duty))) + ((v_in * duty) / (2 * f_sw * l))
```

### 3.24.3 Unsupported arithmetic operators in visitor

Avoid:

```ato
# illustrative invalid in semantic phase
assert x is a | b
assert y is c & d
```

These operators are parsed but rejected semantically.

## 3.25 Quantity form catalog

### 3.25.1 Singleton quantities

```ato
3.3V
1A
10kohm
100nF
2.4MHz
```

### 3.25.2 Bounded quantities

```ato
1.8V to 5.5V
100kHz to 400kHz
0.5mA to 3mA
```

### 3.25.3 Bilateral quantities with absolute tolerance

```ato
10kohm +/- 1kohm
3.3V +/- 0.2V
```

### 3.25.4 Bilateral quantities with relative tolerance

```ato
10kohm +/- 5%
5V +/- 10%
```

### 3.25.5 Unitless values

```ato
ratio: dimensionless
ratio = 0.5
assert ratio within 0.1 to 0.9
```

Use `dimensionless` declaration when representing non-physical scalar ratios.

## 3.26 Field reference and indexing catalog

Examples:

```ato
power
power.hv
i2c.sda.line
gpio[0].line
rows[9].data_out.line
microcontroller.uart[0].base_uart.tx
```

Guidelines:

- Keep field paths readable by introducing local aliases/modules when paths get too deep.
- Avoid unnecessary nested field path access from parent modules if child module can expose cleaner interface.

## 3.27 Retype use catalog

Retype pattern from package code:

```ato
module USB2_0TypeCVerticalConnector from USBTypeCConnector_driver:
    connector -> VerticalUSBTypeCConnector_model
```

This is a clean specialization pattern for package variants.

Prefer this over duplicating full module body for minor package swaps.

## 3.28 Trait statement form catalog

### 3.28.1 Targetless trait on current object

```ato
trait can_bridge_by_name<input_name="input", output_name="output">
```

### 3.28.2 Targeted trait

```ato
trait some_field has_part_removed
```

Use targeted trait forms only when trait semantics clearly belong to nested element.

### 3.28.3 Constructor token note

Grammar allows `trait Type::constructor<...>`.
Use only when codebase conventions require it; canonical usage in repository mostly relies on standard `trait Type<...>`.

## 3.29 For-loop shape catalog

### 3.29.1 Iterate sequence

```ato
for cap in decoupling_caps:
    cap.capacitance = 100nF +/- 20%
    cap.package = "0402"
```

### 3.29.2 Iterate slice

```ato
for cap in decoupling_caps[1:]:
    cap.package = "0402"
```

### 3.29.3 Iterate explicit reference list

```ato
for rail in [power_core, power_io, power_analog]:
    assert rail.voltage within 3.3V +/- 10%
```

### 3.29.4 Invalid body form examples (illustrative invalid)

```ato
# invalid in for body
for x in xs:
    import Resistor

# invalid in for body
for x in xs:
    y = new Resistor
```

## 3.30 Inline declaration-in-connect forms

Grammar permits connectables that are signal/pin declarations.

Valid style (rare, but possible):

```ato
signal mid ~> resistor ~> load.line
pin 1 ~ connector.1
```

Best practice:

- Declare named signal explicitly first in larger modules for readability.

## 3.31 Multi-statement line forms

Grammar permits `;` separated simple statements.

Example:

```ato
r = new Resistor; r.resistance = 10kohm +/- 5%
```

Best practice:

- Avoid this in production modules except very small snippets; one statement per line improves diff readability and review quality.

## 3.32 String statement/docstring behavior

Standalone string as first block statement can be attached as docstring trait behavior.

Pattern:

```ato
module MyModule:
    """
    Human-readable module description.
    """
    pass
```

Prefer first-string docstring for module summary and constraints summary.

## 3.33 Boolean literal and assignment forms

Valid boolean literals:

```ato
True
False
```

Common uses:

```ato
i2c.required = True
chip_select.required = False
```

## 3.34 Declaration statement design patterns

### 3.34.1 Explicit variable declarations for equation-heavy modules

```ato
v_in: V
v_out: V
ratio: dimensionless
```

### 3.34.2 Declare before assert usage

Prefer declaration near top of module before equations for readability.

## 3.35 Practical syntax lint rules

Treat these as \"style-level syntax constraints\" for maintainability:

- one import per line,
- one assert per line,
- avoid chain compare syntax,
- avoid semicolon-packed lines,
- keep bridge chains readable (split if too long),
- group pragma statements at top.

## 3.36 Canonical file preamble templates

### 3.36.1 Minimal stable preamble

```ato
import ElectricPower
import I2C
import Resistor
```

### 3.36.2 Experimental preamble

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")
#pragma experiment("TRAITS")
#pragma experiment("MODULE_TEMPLATING")

import ElectricPower
import I2C
import Resistor
```

Only include pragmas actually used in that file.

# 4. Semantic Invariants

This section is the "do not violate" model. Treat it as executable review criteria.

## 4.1 Invariant classes

Use these invariant classes during review:

- Parsing invariants: what parser accepts.
- Visitor invariants: what semantic translation allows.
- Type/connectivity invariants: what graph-level structure requires.
- Constraint invariants: what solver-compatible expressions require.
- Scope/import invariants: what symbol resolution allows.
- Compatibility invariants: what legacy sugar maps to and what is deprecated.

## 4.2 Import invariants

### 4.2.1 Stdlib import allowlist invariant

For path-less import (`import X`):

- `X` must be in visitor stdlib allowlist, or
- `X` must be recognized trait override alias.

Otherwise import fails semantically.

Review rule:

- If `import Foo` is not a known stdlib type/trait, require `from "..." import Foo`.

### 4.2.2 Path import invariant

`from "path" import Type` is used for package and local module imports.

Review rule:

- keep explicit package paths for external package models;
- avoid converting valid path import into bare import unless verified allowlisted.

## 4.3 Scope invariants

### 4.3.1 No nested block-def invariant

Block definitions must be top-level scope in file structure.

Invalid:

```ato
module Outer:
    module Inner:
        pass
```

### 4.3.2 Unique symbol invariant

Within scope, symbols are unique.

Collision classes:

- block names,
- imports,
- loop aliases.

### 4.3.3 Loop alias collision invariant

For-loop variable cannot collide with existing symbol or field in scope.

Review rule:

- keep loop aliases short but unique (`r`, `cap`, `row`, etc.).

## 4.4 Field/path invariants

### 4.4.1 Field must resolve invariant

Any field reference in assignment/connection must resolve to valid path in current type context after alias translation and overrides.

### 4.4.2 Indexed assignment resolution invariant

For indexed references (`arr[3]`), parent sequence and index member must exist in type graph context.

### 4.4.3 Reference override invariant

Reference override system can transform specific path segments:

- deprecated `reference_shim` maps through `has_single_electric_reference.reference`.
- trait pointer style `has_single_electric_reference.reference` is supported path traversal.

Review rule:

- prefer explicit trait pointer style;
- avoid introducing new `reference_shim` usage.

## 4.5 Instantiation invariants

### 4.5.1 `new` requirement invariant

Type references are not values for assignment; instantiation must use `new`.

### 4.5.2 Array count invariant

`new Type[n]` expects natural-number count.

### 4.5.3 Template pragma invariant

Template args in `new Type<...>` require `MODULE_TEMPLATING` pragma.

### 4.5.4 Index-target with `new` invariant

Assigning `new` to indexed target is invalid by visitor.

Invalid:

```ato
arr[0] = new Resistor
```

Prefer:

```ato
arr = new Resistor[4]
```

## 4.6 Retype invariants

### 4.6.1 Retype is deferred invariant

`target -> Type` records pending retype for later resolution.

Review implications:

- retype can be valid syntactically but fail during later resolution;
- retype should be reserved for clear specialization points, not routine assignment semantics.

### 4.6.2 Retype target existence invariant

Target field path must exist by the time retype is resolved.

## 4.7 Connection invariants

## 4.7.1 `~` direct connect invariant

`~` connects connectables (field refs or inline declarations).

Review rule:

- use `~` for equivalence net joining.

## 4.7.2 Bridge connect gating invariant

`~>` and `<~` require `BRIDGE_CONNECT` experiment.

## 4.7.3 Single direction chain invariant

One directed connect statement may not mix directions.

Invalid:

```ato
a ~> b <~ c
```

## 4.7.4 Bridge path invariant

Directed connect translates through `can_bridge` paths (in/out), not generic net equivalence.

Review rule:

- use bridge connect only when module/interface is intentionally bridgable.

## 4.7.5 Inline declaration in connect invariant

Signal/pin declarations can appear in connectable context and may create paths.

Review rule:

- use this sparingly; prefer explicit prior declaration in readable designs.

## 4.8 Trait invariants

### 4.8.1 Trait pragma invariant

Trait statements require `TRAITS` experiment.

### 4.8.2 Imported trait invariant

Trait type must be imported and resolvable.

### 4.8.3 Trait type validity invariant

Resolved trait type must satisfy trait-type check (`is_trait_type`).

### 4.8.4 Override trait mapping invariant

Some trait names are compatibility aliases and map to canonical traits.

Review rule:

- preserve compatibility where needed in package code;
- prefer canonical trait naming in new design code.

## 4.9 For-loop invariants

### 4.9.1 For-loop pragma invariant

`for` requires `FOR_LOOP` experiment.

### 4.9.2 Iterable shape invariant

Loop iterable must be either:

- list of field refs,
- field-ref sequence with optional slice.

### 4.9.3 Restricted body invariant

Forbidden in loop body:

- import statement,
- pin declaration,
- signal declaration,
- trait statement,
- nested for,
- assignment where RHS is `new`.

### 4.9.4 Deferred sequence execution invariant

Sequence-based loops may defer execution until type graph info is available; list literal loops can execute immediately.

Review rule:

- avoid mixing complex deferred dependencies inside loops unless necessary.

## 4.10 Assertion invariants

### 4.10.1 One-comparison semantic invariant

Parser can parse chained comparison; visitor currently requires exactly one comparison clause.

Bad (fragile):

```ato
assert 1V < x < 5V
```

Good:

```ato
assert x > 1V
assert x < 5V
```

### 4.10.2 Operator mapping invariant

Visitor-supported assert operator mapping:

- `>` -> `GreaterThan`
- `>=` -> `GreaterOrEqual`
- `<` -> `LessThan`
- `<=` -> `LessOrEqual`
- `within` -> `IsSubset`
- `is` -> `Is` (or deprecated literal subset path)

### 4.10.3 `is` literal deprecation invariant

`assert x is <literal>` is deprecated; use `within` for literal domain.

## 4.11 Arithmetic invariants

### 4.11.1 Expression operator invariant

Semantically supported arithmetic binary operators:

- add, subtract, multiply, divide, power.

### 4.11.2 Unsupported parse-but-reject invariant

`|` and `&` may parse but are rejected semantically in visitor.

Review rule:

- never use bitwise-style operators in equations.

## 4.12 Quantity/unit invariants

### 4.12.1 Unit decode invariant

Unit symbols decode through `Units.decode_symbol`; unknown symbols fail with `UnitNotFoundError`.

### 4.12.2 Commensurability invariant

Bounded and bilateral quantity endpoints must be commensurable if both specify units.

### 4.12.3 Bilateral tolerance interpretation invariant

- `%` tolerance is relative.
- unit tolerance is absolute (converted if commensurable).

### 4.12.4 Dimensionless fallback invariant

If no unit symbol appears, quantity is treated as dimensionless.

## 4.13 Assignment-override invariants

Assignment override behavior is field-name based, not arbitrary trait inference.

### 4.13.1 Package override invariant

`field.package = "0402"` maps to `has_package_requirements` with package parsing rules.

### 4.13.2 Picking override invariants

- `lcsc_id` maps supplier-id pick trait.
- `manufacturer` and `mpn` map to assigned manufacturer/part number traits.

### 4.13.3 Required override invariant

`field.required = True` maps to `requires_external_usage` trait.

`False` is typically skip/no-op for this override.

### 4.13.4 Net naming override invariants

- `override_net_name`
- `suggest_net_name`

map to net name suggestion traits with different strictness levels.

### 4.13.5 Default override invariant

`.default` assignment creates `has_default_constraint` trait; default applies only if no explicit bounded value constraint is present.

## 4.14 Name/address behavior invariants

## 4.14.1 Addressor template invariant

Addressor usage often requires templating:

```ato
#pragma experiment("MODULE_TEMPLATING")
addressor = new Addressor<address_bits=3>
```

### 4.14.2 Address relation invariant

Common pattern invariant:

```ato
assert addressor.address is i2c.address
```

### 4.14.3 Default address invariant

Many package modules set default address using `.default`.

Review rule:

- allow downstream override by explicit assignment/assert when integrating multiple devices.

## 4.15 Interface reference invariants

Many logic/signal buses rely on reference rails (`ElectricPower`) for valid voltage semantics.

Common invariant pattern:

```ato
i2c.scl.reference ~ power
i2c.sda.reference ~ power
```

Review rule:

- treat missing reference wiring as likely semantic bug in interface composition.

## 4.16 Power-path invariants

For bridged power modules (`LDO`, `fuse`, `monitor`, etc.):

- input/output rails should be explicit interfaces,
- bridge trait path should be clear,
- ground/low-side consistency should be explicit.

## 4.17 Compatibility/deprecation invariants

Known compatibility areas:

- `reference_shim` is deprecated compatibility path.
- some trait aliases are compatibility wrappers.
- multi-import one-liner is deprecated.

Review rule:

- do not churn legacy forms unless requested,
- prefer canonical forms in new code.

## 4.18 Review-time semantic checklist (strict)

For each changed `.ato` file:

- check required pragma gates for used features,
- check all imports resolve under allowlist/path rules,
- check every `new` form validity,
- check all `assert` operators and clause count semantics,
- check for unsupported arithmetic operators,
- check commensurable units for bounded/bilateral quantities,
- check for reference wiring on logic/signal buses,
- check bridge chain direction consistency,
- check overrides map to supported fields only,
- check loop body restrictions.

## 4.19 Connectivity invariants by interface family

This subsection translates abstract invariants into concrete interface-family checks.

### 4.19.1 Power rail family (`ElectricPower`)

Invariant expectations:

- rails expose both high and low potentials (`hv`, `lv`),
- downstream consumers attach to same rail pair unless intentional domain split exists,
- inline components in rail paths use bridge semantics only if physically series.

Reviewer checks:

- no accidental short between unrelated rails,
- no missing low-side continuity across modules,
- voltage constraints exist on externally provided rails.

### 4.19.2 Logic/signal family (`ElectricLogic`, `ElectricSignal`)

Invariant expectations:

- line has a coherent reference rail,
- shared buses agree on reference domain,
- pullups/pulldowns connect to correct rail side.

Reviewer checks:

- each logic/signal line that crosses module boundaries has an explicit reference relation,
- no pullup accidentally connected to `lv` when intent is `hv` (or vice versa),
- open-drain/open-source outputs include required biasing where module behavior assumes it.

### 4.19.3 Differential family (`DifferentialPair`, `USB data`, Ethernet pairs)

Invariant expectations:

- positive and negative lines are consistently mapped,
- impedance constraints are present where signal integrity matters,
- pair references are consistent.

Reviewer checks:

- avoid swapping `p`/`n` unless intentional and documented,
- keep both sides of pair referenced to appropriate domain,
- avoid splitting pair routing intent across unrelated modules.

### 4.19.4 Bus family (`I2C`, `SPI`, `UART`, `I2S`)

Invariant expectations:

- bus endpoint interfaces are connected as interface-level links (`bus ~ bus`),
- bus-specific constraints are present (`address`, `frequency`, etc.) where needed,
- helper passives (pullups, decouplers) are attached to correct rails.

Reviewer checks:

- I2C address collisions mitigated by address constraints/defaults,
- SPI has explicit chip-select strategy,
- UART reference domains aligned across participants,
- I2S role mapping (`sd`, `ws`, `sck`) consistent with target parts.

## 4.20 Constraint graph invariants

Constraint graph quality is as important as syntax validity.

### 4.20.1 Reachability invariant

Every declared variable and key component parameter should be reachable through constraints to a module input, output, or externally constrained value.

Symptoms of violation:

- variable declared but only appears once,
- equations exist but cannot influence pickable component parameters,
- output interface behavior unconstrained.

### 4.20.2 Non-circular triviality invariant

Avoid useless self-referential or tautological constraints.

Bad:

```ato
assert v_out is v_out
```

Also avoid equation sets that are algebraically circular without anchor constraints.

### 4.20.3 Contradiction-avoidance invariant

Do not combine mutually incompatible hard constraints on the same parameter.

Bad pattern:

```ato
assert power.voltage within 3.3V +/- 1%
assert power.voltage within 5V +/- 1%
```

unless this is intentionally impossible for validation tests.

### 4.20.4 Bounded literal preference invariant

For component picking, bounded/toleranced literals are often better than exact singletons unless exact value is required.

Reason:

- exact singleton can overconstrain available stock/package combinations.

## 4.21 Picking invariants

### 4.21.1 Pickability signal invariant

Setting fields like `lcsc_id`, `manufacturer`, `mpn`, and `package` has semantic meaning via trait overrides.

Review rule:

- if a code path relies on lock-in behavior, verify the corresponding override field is used exactly and correctly.

### 4.21.2 Package-format invariant

Package strings must be parseable by package override logic and SMD size enum interpretation.

Practical rule:

- use known footprint strings (`0402`, `0603`, `R0402`, `C0402`) consistent with repository patterns.

### 4.21.3 Hybrid picking invariant

Hybrid strategy should be deliberate:

- manual locks where necessary,
- constraints for all other pickable components.

### 4.21.4 Removed-part invariant

`has_part_removed` behavior can intentionally suppress picking expectations in some patterns. Do not remove this trait casually from modules that intentionally represent non-BOM placeholders or integration stubs.

## 4.22 Address and identity invariants

### 4.22.1 Address identity invariant

When using Addressor patterns, `assert addressor.address is i2c.address` should hold unless module intentionally separates logical and hardware address behavior.

### 4.22.2 Default identity invariant

If module sets `i2c.address.default`, integration-level explicit address constraints should override without contradiction.

### 4.22.3 Bus identity invariant

When multiple devices share one bus instance, they should share bus reference domains and frequency constraints unless intentional bus segmentation exists.

## 4.23 Bridge-connect invariants in depth

### 4.23.1 Structural bridge invariant

A bridge chain should represent a physically serial path or protocol chain.

Examples:

- power path through fuse/regulator/sensor shunt,
- serial data daisy chain through LED strips.

Do not use bridge chain for arbitrary relationship expression that is not serial.

### 4.23.2 Trait path invariant

Bridge semantics rely on `can_bridge` in/out traversal.
If a module is used in bridge chain, ensure it either:

- natively exposes relevant `can_bridge` trait semantics,
- or defines compatibility trait mapping (`can_bridge_by_name`).

### 4.23.3 Ground continuity invariant in power bridge modules

For power bridge modules with separate in/out rails:

- ensure low-side relation (`lv`) continuity is explicit where expected,
- avoid accidental floating low-side by omission.

## 4.24 For-loop invariants in depth

### 4.24.1 Expansion determinism invariant

Loops should expand deterministically over intended sequences.

Reviewer checks:

- sequence indexing is stable,
- slice boundaries are intentional,
- no hidden dependence on unspecified ordering.

### 4.24.2 New-child creation separation invariant

Create arrays outside loops, then constrain/connect within loop.

Bad:

```ato
# invalid
for i in xs:
    xs2[i] = new Resistor
```

Good:

```ato
xs2 = new Resistor[8]
for r in xs2:
    r.package = "0402"
```

## 4.25 Module API invariants

### 4.25.1 Required-interface invariant

Interfaces marked `required = True` (override trait behavior) should generally be connected by parent modules; review usage examples for compliance.

### 4.25.2 Minimal API invariant

Public API should expose stable interfaces and key knobs, not incidental internals.

### 4.25.3 API consistency invariant across variants

For family modules (`Base`, variant subclasses), keep public interface names stable across variants to preserve integrator portability.

## 4.26 Compatibility invariants for legacy sugar

Compatibility sugar is useful but should be handled intentionally.

### 4.26.1 `reference_shim` compatibility invariant

If present in legacy code, behavior is transformed; new code should prefer explicit trait-pointer path.

### 4.26.2 Trait alias compatibility invariant

Aliases like `has_single_electric_reference_shared` may map to canonical traits. Avoid broad rename churn unless migration is explicit project goal.

### 4.26.3 Deprecation warning tolerance invariant

Warnings in compatibility paths should not be silently ignored in new modules; treat as migration prompts.

## 4.27 Unit and dimension invariants in depth

### 4.27.1 Dimension preservation invariant

Equations should preserve dimensional consistency.

Examples:

- resistance = voltage / current is dimensionally valid,
- resistance = voltage + current is invalid by dimension.

### 4.27.2 Frequency and time inverse invariant

If relating period and frequency:

```ato
assert period is 1 / frequency
```

ensure units align (`s` and `Hz`).

### 4.27.3 Percent semantics invariant

Percent applies as relative factor, not absolute offset unless converted intentionally.

## 4.28 Reliability invariants for package modules

Use this when reviewing package driver `.ato` files:

- decoupling exists for each major power domain,
- pullups for open-drain pins are present where required,
- fixed address or strap behavior documented and constrained,
- reset/enable defaults are explicit and safe,
- package exposed pads/grounds connected as datasheet requires,
- usage file demonstrates minimal valid integration.

## 4.29 Invariant severity mapping for reviews

Use this severity model:

- Critical:
  - syntax invalidity,
  - missing required pragma,
  - contradictory hard constraints,
  - invalid bridge direction mixing.
- High:
  - incorrect reference domain wiring,
  - unresolved field paths,
  - wrong import model.
- Medium:
  - underconstrained picks,
  - unstable defaults,
  - noisy API leakage.
- Low:
  - readability/style concerns.

## 4.30 Invariant-driven rewrite heuristics

If a module fails multiple invariants, rewrite in this order:

1. restore parser/visitor validity,
2. restore interface/reference correctness,
3. restore constraint coherence,
4. restore picking strategy clarity,
5. improve readability.

## 4.31 Automated review prompts (for LLM use)

When using this skill to review code, ask:

- Which pragma-gated constructs are present, and are gates enabled?
- Which asserts are chain-style and should be split?
- Which quantities may be non-commensurable?
- Which fields rely on compatibility sugar that should be modernized?
- Which interfaces lack explicit reference connections?
- Which modules are overexposed at API boundary?

## 4.32 Invariant checklist for merge readiness

A module is merge-ready when:

- all critical and high invariant violations are resolved,
- medium issues are either resolved or explicitly accepted,
- usage example remains valid and representative,
- no unsupported constructs remain.

# 5. Parameters, Units, Constraints, Solver-Aware Authoring

## 5.1 Parameter modeling principles

Treat every useful electrical property as a parameter domain, not a hard singleton, unless singleton is required.

Good default hierarchy:

1. broad physically valid bounds,
2. narrower system requirement bounds,
3. optional exact values where required by architecture.

## 5.2 Domain sizing strategy

### 5.2.1 Too narrow risks contradiction

Overly tight constraints can make solver/picker infeasible.

Example risk:

```ato
assert regulator.power_out.voltage within 3.300V +/- 0.01%
```

Use realistic tolerance unless exactness is mandatory.

### 5.2.2 Too broad risks underconstrained picks

Overly wide constraints produce unstable or low-quality picks.

Example risk:

```ato
assert resistor.resistance within 1ohm to 10Mohm
```

Narrow with intended function.

## 5.3 Equation authoring patterns

### 5.3.1 Use redundant but consistent equations for solvability

Pattern from `examples/equations/equations.ato`:

- include multiple algebraically equivalent expressions that expose relation from different directions.

Reason:

- improves solver propagation depending on which variables are constrained upstream.

### 5.3.2 Keep equation graph connected

If a declared variable is never tied to observable interfaces or component parameters, it is dead semantic weight.

Review rule:

- each variable should participate in at least one meaningful assert relation connected to design outputs/inputs.

## 5.4 Units and tolerance authoring

### 5.4.1 Prefer explicit units everywhere

Use units for all electrical quantities:

- voltage: `V`
- current: `A`
- resistance: `ohm`/`kohm`
- capacitance: `F`/`uF`/`nF`
- frequency: `Hz`

### 5.4.2 Prefer bilateral tolerances for real components

Example:

```ato
res.resistance = 10kohm +/- 1%
cap.capacitance = 100nF +/- 20%
```

### 5.4.3 Use bounded ranges for interface envelopes

Example:

```ato
assert power.voltage within 2.7V to 5.5V
assert i2c.frequency within 100kHz to 400kHz
```

### 5.4.4 Commensurability-safe forms

Valid (commensurable):

```ato
assert power.voltage within 3300mV to 3.6V
```

Invalid (non-commensurable):

```ato
# illustrative invalid
assert power.voltage within 3.3V to 5A
```

## 5.5 `within` vs `is`

Choose operators intentionally:

- `within`: subset/bounds relation (recommended for literal/range constraints)
- `is`: equivalence relation between expressions/parameters

Good:

```ato
assert power.voltage within 3.3V +/- 5%
assert addressor.address is i2c.address
```

Avoid `is` with literal unless compatibility pressure forces it.

## 5.6 Auto-picked component workflow

Auto-pick is driven by trait and parameter constraints.

Use this layering:

1. Electrical constraints (value/rating/range).
2. Package constraints (`package = "0402"`) where layout/BOM policy requires.
3. Optional explicit part constraints for deterministic BOM:
   - `lcsc_id`
   - `manufacturer`
   - `mpn`

Examples:

```ato
r = new Resistor
r.resistance = 10kohm +/- 5%
r.package = "0402"

led = new LED
led.lcsc_id = "C2286"
```

## 5.7 Manual pick vs auto pick

When to choose auto pick:

- early architecture,
- value-driven passives,
- supply flexibility desired.

When to choose manual pick:

- known validated BOM part,
- lifecycle or sourcing constraints,
- compliance/certified part requirements.

Hybrid pattern:

- constrain electrically and package-wise,
- lock only high-risk parts (MCU, RF, power converters),
- leave low-risk passives auto-picked.

## 5.8 `.default` parameter behavior

`param.default = ...` is for package/module defaults that users may override.

Recommended usage:

- package/module author sets defaults,
- integrator can override with explicit `assert`/assignment.

Example:

```ato
i2c.address.default = 0x20
```

## 5.9 Interface parameter practices

### 5.9.1 Power interfaces

Constrain:

- `voltage`
- optional `max_current`
- optional `max_power`

### 5.9.2 Bus interfaces

Constrain:

- address, frequency, bus-level references where relevant.

### 5.9.3 Logic/signal references

Always tie reference rails unless intentionally abstract.

## 5.10 Solver-aware equation patterns

### 5.10.1 Voltage divider pattern

Useful relation set:

```ato
assert r_total is r_top.resistance + r_bottom.resistance
assert v_out is v_in * r_bottom.resistance / r_total
assert max_current is v_in / r_total
```

### 5.10.2 Regulator feedback divider pattern

Constrain total resistance and ratio windows, not only exact target voltage, to keep pick search practical.

### 5.10.3 Current-sense shunt pattern

Constrain shunt by allowed drop and target current range:

```ato
assert shunt.resistance <= shunt_drop / max_current * 1.1
assert shunt.resistance >= shunt_drop / max_current * 0.9
```

## 5.11 High-probability failure modes and mitigations

### 5.11.1 Contradiction by literal

Cause:

- multiple exact incompatible assignments.

Mitigation:

- switch one or more to bounded/toleranced `within` intervals.

### 5.11.2 Underconstrained pick

Cause:

- broad/no constraints for pickable component.

Mitigation:

- add core electrical bounds + package constraint.

### 5.11.3 Invalid unit symbol

Cause:

- misspelled or unsupported symbol.

Mitigation:

- use known symbols (`V`, `A`, `ohm`, `F`, `Hz`, `rpm`, etc.) and SI prefixes.

### 5.11.4 Non-commensurable arithmetic

Cause:

- operations mixing incompatible dimensions.

Mitigation:

- inspect each operand unit and convert to commensurable dimensions.

## 5.12 Unit symbol quick map (selected)

Common symbols from units registry:

- voltage: `V`
- current: `A`
- resistance: `ohm` (also `Omega` symbol alias exists)
- capacitance: `F`
- power: `W`
- frequency: `Hz`
- percent: `%`
- dimensionless: `dimensionless`

SI prefixes are supported (`m`, `u`/`micro`, `n`, `k`, `M`, etc.) through unit decoder.

## 5.13 Authoring templates for constraint-heavy modules

Template pattern:

```ato
module Template:
    in_power = new ElectricPower
    out_power = new ElectricPower

    # Declared parameters
    target_voltage: V
    max_current: A

    # Core architecture constraints
    assert out_power.voltage within target_voltage +/- 3%
    assert out_power.max_current <= max_current

    # Interface connectivity constraints
    assert in_power.voltage >= out_power.voltage
```

Then add component-level equations and package constraints incrementally.

# 6. Stdlib / Interface Map

This section maps common stdlib interfaces/modules to authoring intent and "choose X vs Y" guidance.

## 6.1 Core electrical primitives

## 6.1.1 `Electrical`

Use when you need an untyped electrical connection point.

Choose `Electrical` when:

- you only need net continuity,
- no explicit reference rail semantics are required.

Choose `ElectricSignal`/`ElectricLogic` instead when voltage-reference semantics matter.

## 6.1.2 `ElectricPower`

Represents two-rail power (`hv`, `lv`) with voltage/current/power params.

Choose for:

- supply rails,
- battery/system power paths,
- bus references.

Key fields:

- `hv`, `lv`
- `voltage`
- `max_current`
- `max_power`

Legacy aliases `vcc` and `gnd` exist for compatibility; prefer `hv`/`lv`.

## 6.1.3 `ElectricSignal`

Single signal line plus explicit `reference` power interface.

Choose for:

- analog or general signal with amplitude relative to reference.

Key fields:

- `line`
- `reference`

## 6.1.4 `ElectricLogic`

Logic signal (line + reference), logic-oriented semantics.

Choose for:

- GPIOs,
- digital control lines,
- interrupts, reset, enable pins.

Key fields:

- `line`
- `reference`

## 6.2 Bus interfaces

## 6.2.1 `I2C`

Use for two-wire bus with address and frequency constraints.

Key fields/params:

- `scl`, `sda`
- `address`
- `frequency`

Typical integration pattern:

```ato
i2c.scl.reference ~ power
i2c.sda.reference ~ power
assert i2c.address within 0x20 to 0x27
```

## 6.2.2 `SPI`

Use for 3-wire data+clock bus (plus external CS lines as needed).

Key fields:

- `sclk`, `miso`, `mosi`
- `frequency`

Choose `MultiSPI` if multiple data lanes are needed.

## 6.2.3 `MultiSPI`

Use for multi-lane SPI/QSPI style interfaces.

Key fields:

- `clock`
- `chip_select`
- `data[n]`

Usually instantiated with module templating/factory-backed type in package code.

## 6.2.4 `UART_Base` and `UART`

Use `UART_Base` for minimal TX/RX.

Use `UART` for full control-line capable interface.

`UART` includes `base_uart` plus RTS/CTS/etc.

## 6.2.5 `I2S`

Audio serial bus.

Key fields:

- `sd`, `ws`, `sck`
- `sample_rate`, `bit_depth`

## 6.3 USB and differential interfaces

## 6.3.1 `DifferentialPair`

Use for paired differential signals (`p`, `n`) with impedance param.

## 6.3.2 `USB2_0_IF` and `USB2_0`

`USB2_0_IF` contains:

- differential data pair (`d`)
- bus power (`buspower`)

`USB2_0` wraps `usb_if` and is often easier as top-level module interface.

Choose `USB2_0` for module interfaces, `USB2_0_IF` when you need direct field-level composition.

## 6.4 Misc interfaces commonly used in packages

Commonly imported in package corpus:

- `SWD`
- `JTAG`
- `Ethernet`
- `XtalIF`
- `I2C`, `SPI`, `I2S`, `UART`

Use package implementations as pattern references for pin mapping and decoupling scaffolds.

## 6.5 Core passive/active modules

Frequent stdlib modules:

- `Resistor`
- `Capacitor`
- `Inductor`
- `Diode`
- `LED`
- `Fuse`
- `ResistorVoltageDivider`

These are typically auto-pick enabled and respond well to value + package constraints.

## 6.6 Trait utilities relevant to ato authoring

Common traits encountered in `.ato`:

- `can_bridge_by_name` (compatibility alias behavior)
- `has_single_electric_reference`
- `has_part_removed`
- `has_package_requirements`
- `requires_external_usage` (via `.required = True` override)

## 6.7 Choose X vs Y quick guidance

### 6.7.1 `ElectricLogic` vs `ElectricSignal`

Choose `ElectricLogic` for digital semantics and GPIO-like lines.

Choose `ElectricSignal` for analog/general signal rails.

### 6.7.2 `~` vs `~>`

Choose `~` for simple net/interface equivalence.

Choose `~>` for explicit inline bridging through bridgable elements.

### 6.7.3 `within` vs `is`

Choose `within` for domain/range/literal constraints.

Choose `is` for equation identity between parameters/expressions.

Tangible examples:

```ato
module RuleExamples:
    power = new ElectricPower
    i2c = new I2C
    addressor = new Addressor<address_bits=3>
    target_v: V

    # `within`: constrain a value to an allowed domain/range
    assert power.voltage within 3.3V +/- 5%
    assert i2c.frequency within 100kHz to 400kHz

    # `is`: declare identity/equality between two expressions/parameters
    assert addressor.address is i2c.address
    assert target_v is power.voltage
```

### 6.7.4 Auto pick vs explicit part lock

Auto pick for passives and flexible BOM stages.

Explicit lock for lifecycle-critical or already-qualified parts.

### 6.7.5 `module` vs `interface`

Choose `interface` for reusable connectable bus/signal abstraction.

Choose `module` for concrete reusable hardware blocks with components and equations.

## 6.8 Package ecosystem building blocks

In package repositories, common structure is:

- top-level driver module (`vendor-part.ato`),
- `usage.ato` demonstrating integration,
- `parts/` folder with package-specific mapped parts,
- occasional `family/model` files.

Design guidance:

- keep public driver interface stable,
- isolate package pin mapping internally,
- expose clean interfaces (`power`, `i2c`, `spi`, `gpio`, etc.),
- apply sane defaults with override points.

# 7. Architecture Patterns

This section is prescriptive: use these patterns to keep ato designs modular, solver-friendly, and package-reusable.

## 7.1 Pattern: Interface-first module boundaries

### Intent

Expose external behavior as interfaces first; keep internals private.

### Template

```ato
module SensorBoard:
    power = new ElectricPower
    i2c = new I2C

    # Internal blocks
    sensor = new SomeSensor
    pullups = new Resistor[2]

    power ~ sensor.power
    i2c ~ sensor.i2c
```

### Why this is correct

- integration points are explicit and stable,
- internals can be refactored without breaking parent modules.

### Anti-pattern

Exposing internal package pins directly as public API.

## 7.2 Pattern: Rail-centric power architecture

### Intent

Model power as named `ElectricPower` rails and bridge modules between them.

### Template

```ato
#pragma experiment("BRIDGE_CONNECT")

module PowerTree:
    vin = new ElectricPower
    vout = new ElectricPower
    fuse = new Fuse
    ldo = new TI_TLV75901

    vin ~> fuse ~> ldo ~> vout
```

### Why this is correct

- topology is readable,
- bridge semantics mirror physical inline flow,
- easy insertion/removal of protection and measurement blocks.

## 7.3 Pattern: Bus spine with localized adapters

### Intent

Create one bus spine and branch through dedicated adapter modules.

### Template

```ato
module App:
    i2c_bus = new I2C
    mcu = new MCU
    expander = new NXP_PCF8574
    sensor = new Sensirion_SCD41

    i2c_bus ~ mcu.i2c
    i2c_bus ~ expander.i2c
    i2c_bus ~ sensor.i2c
```

### Why this is correct

- centralized bus constraints (frequency/reference),
- easy multi-device address management,
- fewer duplicated pullup patterns.

## 7.4 Pattern: Addressor-driven address configuration

### Intent

Use Addressor to encode address pin logic from desired address constraints.

### Template

```ato
#pragma experiment("MODULE_TEMPLATING")

addressor = new Addressor<address_bits=3>
addressor.base = 0x20
assert addressor.address is i2c.address
```

### Why this is correct

- constraints drive hardware pin states,
- avoids ad-hoc hand-set address pin wiring logic.

## 7.5 Pattern: Defaults with override points

### Intent

Set package defaults via `.default` while permitting integrator overrides.

### Template

```ato
i2c.address.default = 0x20
```

### Why this is correct

- reusable module gets sensible baseline,
- parent design can still resolve address conflicts.

## 7.6 Pattern: Constraint layering

### Intent

Add constraints from generic to specific in layers:

1. datasheet-safe envelope,
2. system target,
3. manufacturing/package constraints.

### Example

```ato
assert power.voltage within 2.7V to 5.5V
assert power.voltage within 3.3V +/- 5%
res.package = "0402"
```

### Why this is correct

- solver gets physically valid space and intent target,
- picker gets practical package guidance.

## 7.7 Pattern: Functional equation modules

### Intent

Encapsulate equations in reusable module (divider, sensor scaling, shunt monitor).

### Template

```ato
module Divider:
    in_power = new ElectricPower
    out_sig = new ElectricSignal
    r_top = new Resistor
    r_bottom = new Resistor

    in_power.hv ~> r_top ~> out_sig.line ~> r_bottom ~> in_power.lv

    v_in: V
    v_out: V
    i_div: A
    assert v_in is in_power.voltage
    assert v_out is out_sig.reference.voltage
    assert r_bottom.resistance is v_out / i_div
```

### Why this is correct

- equations are reusable and testable,
- interface abstraction stays clean.

## 7.8 Pattern: Adapter modules for package pin mapping

### Intent

Keep package-specific pin mapping in dedicated module and expose abstract interface.

### Why this matters

- retarget package/variant without changing parent architecture,
- isolates long pin maps to one file.

## 7.9 Pattern: Bridgeable data chains

### Intent

For daisy-chain protocols (addressable LEDs, pass-through interfaces), define explicit input/output and trait bridge mapping.

### Template

```ato
#pragma experiment("TRAITS")
#pragma experiment("BRIDGE_CONNECT")

module DataChain:
    data_in = new ElectricLogic
    data_out = new ElectricLogic
    trait can_bridge_by_name<input_name="data_in", output_name="data_out">
```

### Why this is correct

- enables clean `a ~> chain ~> b` syntax,
- documents path intent explicitly.

## 7.10 Pattern: Decoupling as local invariant

### Intent

Each powered IC/module should own its decoupling constraints and connectivity.

### Template

```ato
decoup = new Capacitor
decoup.capacitance = 100nF +/- 20%
decoup.package = "0402"
power.hv ~> decoup ~> power.lv
```

### Why this is correct

- avoids relying on external caller to remember mandatory decoupling,
- keeps module electrically self-consistent.

## 7.11 Pattern: Separate usage examples from drivers

### Intent

Keep `usage.ato` concise and integration-focused; keep full constraints in driver module.

### Why this is correct

- easier onboarding,
- prevents duplicate or divergent constraint logic.

## 7.12 Pattern: Controlled explicit part locking

### Intent

Lock only critical parts, leave commoditized parts auto-picked.

### Example

- lock MCU, PMIC, RF front-end;
- auto-pick resistors/caps by value and package.

### Why this is correct

- balances deterministic BOM and sourcing flexibility.

## 7.13 Pattern: Public API minimalism

### Intent

Expose only interfaces and high-level params likely needed by parent design.

Avoid exposing internals like helper pullups or intermediate nets unless required.

### Why this is correct

- preserves module evolution freedom,
- reduces accidental coupling.

## 7.14 Pattern: Explicit net naming only where valuable

Use `override_net_name` for nets that must stay stable (test points, external connectors, protocol rails).

Avoid overusing net name overrides for every internal net, can lead to net name collisions.

## 7.15 Pattern: Composition over inheritance

Use `from Parent` inheritance for clear family variants.

Prefer explicit composition for subsystem assembly.

### Why

- inheritance is useful for variant specialization,
- composition is better for system architecture readability.

## 7.16 Pattern: Family/model split in packages

Common package structure:

- base model with shared behavior,
- family/variant modules inheriting base,
- package drivers selecting concrete package and constraints.

This appears in ESP32 package examples and reduces duplication.

## 7.17 Pattern: Reviewer architecture rubric

For any new module, check:

- Are public interfaces clear and minimal?
- Are rails and references explicit?
- Is bridge syntax used only where physically meaningful?
- Are defaults overridable?
- Is package pin mapping isolated?
- Are equations both meaningful and solvable?

# 8. Annotated Example Corpus

All examples below are based on real repository files or package modules. Code blocks are valid ato unless explicitly marked otherwise.

## 8.1 `quickstart` (from `examples/quickstart/quickstart.ato`)

### Source-derived snippet

```ato
import Resistor

module App:
    r1 = new Resistor
    r1.resistance = 50kohm +/- 10%
```

### Why this is correct

- Minimal valid instantiation + parameter assignment.
- Uses `new` correctly.
- Uses bilateral percentage tolerance, which solver/picker can consume.

### Review notes

- This pattern is baseline for passive instantiation.
- If layout policy exists, add `r1.package = "0402"`.

## 8.2 `passives` (from `examples/passives/passives.ato`)

### Source-derived snippet

```ato
#pragma experiment("BRIDGE_CONNECT")

import Resistor
import Capacitor
import Diode

module App:
    resistor = new Resistor
    capacitor = new Capacitor
    diode = new Diode

    assert resistor.resistance within 10kohm +/- 10%
    assert capacitor.capacitance within 100nF +/- 10%
    assert diode.forward_voltage within 0.5V to 0.8V

    resistor.unnamed[0] ~ diode.anode
    resistor.unnamed[1] ~ capacitor.unnamed[0]
    diode.cathode ~ capacitor.unnamed[1]
```

### Why this is correct

- Uses realistic bounded/toleranced domains.
- Demonstrates direct connectivity graph for three passive/semiconductor primitives.
- Avoids unsupported enum-string override for capacitor temp coefficient in this example.

### Common extension

Add package constraints:

```ato
resistor.package = "0402"
capacitor.package = "0402"
```

## 8.3 `equations` (from `examples/equations/equations.ato`)

### Source-derived snippet

```ato
import Resistor
import ElectricPower
import ElectricSignal

module VoltageDivider:
    power = new ElectricPower
    output = new ElectricSignal

    r_bottom = new Resistor
    r_top = new Resistor

    v_in: V
    v_out: V
    max_current: A
    r_total: ohm
    ratio: dimensionless

    power.hv ~> r_top ~> output.line ~> r_bottom ~> power.lv

    assert v_out is output.reference.voltage
    assert v_in is power.voltage

    assert r_total is r_top.resistance + r_bottom.resistance
    assert v_out is v_in * r_bottom.resistance / r_total
    assert max_current is v_in / r_total
    assert ratio is r_bottom.resistance / r_total
```

### Why this is correct

- Declares physically meaningful variables with units.
- Uses equations to couple interface behavior and component values.
- Provides multiple relation pathways for solver propagation.

### Solver-aware notes

- Keep equations algebraically consistent; contradictions here are hard failures.
- If underconstrained, constrain one of `max_current`, `ratio`, or `v_out` target window.

## 8.4 `pick_parts` (from `examples/pick_parts/pick_parts.ato`)

### Source-derived snippet

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")

import ElectricPower
import LED
import Resistor

module App:
    power = new ElectricPower

    current_limiting_resistors = new Resistor[2]
    for resistor in current_limiting_resistors:
        resistor.resistance = 10kohm +/- 20%
        resistor.package = "R0402"

    leds = new LED[2]
    leds[0].lcsc_id = "C2286"
    leds[1].manufacturer = "Hubei KENTO Elec"
    leds[1].mpn = "KT-0603R"

    power.hv ~> current_limiting_resistors[0] ~> leds[0] ~> power.lv
    power.hv ~> current_limiting_resistors[1] ~> leds[1] ~> power.lv
```

### Why this is correct

- Demonstrates hybrid picking strategy:
  - auto-pick constrained passives,
  - explicit locked LED selections.
- Uses bridge topology to model series current path.

### Review focus points

- `FOR_LOOP` and `BRIDGE_CONNECT` pragmas are required.
- Package string format is parsed by override (`R0402` accepted).

## 8.5 `i2c` (from `examples/i2c/i2c.ato`)

### Source-derived snippet

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("MODULE_TEMPLATING")

import Addressor
import I2C
import ElectricPower
import ElectricLogic
import Capacitor
import Resistor

module TI_TCA9548A:
    power = new ElectricPower
    i2c = new I2C
    reset = new ElectricLogic
    i2cs = new I2C[8]

    assert power.voltage within 1.65V to 5.5V

    addressor = new Addressor<address_bits=3>
    addressor.base = 0x70
    assert addressor.address is i2c.address

    reset_pullup = new Resistor
    reset_pullup.resistance = 10kohm +/- 1%
    reset.line ~> reset_pullup ~> reset.reference.hv

    decoupling_caps = new Capacitor[2]
    decoupling_caps[0].capacitance = 100nF +/- 20%
    decoupling_caps[1].capacitance = 2.2uF +/- 20%
    for cap in decoupling_caps:
        power.hv ~> cap ~> power.lv
```

### Why this is correct

- Uses Addressor to relate configurable hardware address pins and bus address parameter.
- Applies bus reference and decoupling patterns.
- Exposes upstream/downstream I2C interfaces clearly.

### Integration guidance

In parent module:

```ato
assert mux.addressor.address is 0x71
```

This constrains line levels indirectly through Addressor behavior.

## 8.6 `esp32_minimal` (from `examples/esp32_minimal/esp32_minimal.ato`)

### Source-derived snippet

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower

from "atopile/usb-connectors/usb-connectors.ato" import USB2_0TypeCHorizontalConnector
from "atopile/ti-tlv75901/ti-tlv75901.ato" import TI_TLV75901
from "atopile/espressif-esp32-c3/espressif-esp32-c3-mini.ato" import ESP32_C3_MINI_1

module ESP32_MINIMAL:
    micro = new ESP32_C3_MINI_1
    usb_c = new USB2_0TypeCHorizontalConnector
    ldo_3V3 = new TI_TLV75901

    power_3v3 = new ElectricPower

    usb_c.usb.usb_if.buspower ~> ldo_3V3 ~> power_3v3
    power_3v3 ~ micro.power

    ldo_3V3.v_in = 5V +/- 5%
    ldo_3V3.v_out = 3.3V +/- 3%

    usb_c.usb.usb_if ~ micro.usb_if
```

### Why this is correct

- Captures realistic minimal embedded topology:
  - USB bus power -> regulator -> MCU rail.
- Uses bridge connect for power path composition.
- Keeps external interfaces at module boundaries.

### Reviewer cautions

- Verify exact field names (`v_in`/`v_out` vs `power_in`/`power_out`) against concrete regulator module version.
- Maintain pragma for bridge connect.

## 8.7 `layout_reuse` (from `examples/layout_reuse/layout_reuse.ato`)

### Source-derived snippet

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")

import Resistor

module Sub:
    r_chain = new Resistor[3]
    for r in r_chain:
        r.resistance = 1kohm +/- 20%
        r.package = "R0402"

    r_chain[0] ~> r_chain[1] ~> r_chain[2]

module Top:
    sub_chains = new Sub[3]

    sub_chains[0].r_chain[2] ~> sub_chains[1].r_chain[0]
    sub_chains[1].r_chain[2] ~> sub_chains[2].r_chain[0]
    sub_chains[2].r_chain[2] ~> sub_chains[0].r_chain[0]
```

### Why this is correct

- Shows hierarchical reuse of sub-layout-ready modules.
- Demonstrates bridge chaining across module boundaries.
- Uses loop for repetitive constraints.

### Design intent note

This pattern is valuable when module-level layout reuse (group routing/placement) is part of workflow.

## 8.8 `led_badge` (from `examples/led_badge/led_badge.ato`)

### Source-derived snippet

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")

import ElectricPower
import Resistor
import ElectricLogic
import I2S
import can_bridge_by_name

from "atopile/usb-connectors/usb-connectors.ato" import USBTypeCConnector_driver
from "atopile/ti-tps63020/ti-tps63020.ato" import TPS63020_driver
from "atopile/ti-bq25185/ti-bq25185.ato" import TI_BQ25185
from "atopile/espressif-esp32-c3/espressif-esp32-c3-mini.ato" import ESP32_C3_MINI_1

module LED_BADGE:
    microcontroller = new ESP32_C3_MINI_1
    usb_c = new USBTypeCConnector_driver
    buck_boost = new TPS63020_driver
    charger = new TI_BQ25185

    power_3v3 = new ElectricPower

    usb_c.usb.usb_if.buspower ~ charger.power_input
    charger.power_system ~> buck_boost ~> power_3v3

    power_3v3 ~ microcontroller.power
```

### Why this is correct

- Composes full portable system power path with charging and regulation.
- Uses module interfaces and bridge semantics to preserve architecture clarity.
- Demonstrates realistic multi-subsystem composition.

### Advanced pattern in same example

LED strip/grid modules define bridgeable data flow via trait:

```ato
trait can_bridge_by_name<input_name="data_in", output_name="data_out">
```

This enables ergonomic chained composition for large LED arrays.

## 8.9 Package-derived example: I2C GPIO expander (`microchip-mcp23017`)

### Source-derived snippet

```ato
#pragma experiment("MODULE_TEMPLATING")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")

import ElectricPower
import I2C
import ElectricLogic
import Resistor
import Addressor

module Microchip_MCP23017:
    power = new ElectricPower
    i2c = new I2C
    gpio_a = new ElectricLogic[8]
    gpio_b = new ElectricLogic[8]

    assert power.voltage within 1.8V to 5.5V

    addressor = new Addressor<address_bits=3>
    addressor.base = 0x20
    assert addressor.address is i2c.address
    i2c.address.default = 0x20

    for gpio in gpio_a:
        gpio.reference ~ power
```

### Why this is correct

- Strong public interface contract.
- Address defaults + override path for bus coexistence.
- Explicit reference handling for GPIO ports.

### Integration note

In usage, set shared bus refs and optionally override address per instance.

## 8.10 Package-derived example: Power monitor bridge (`ti-ina228`)

### Source-derived snippet

```ato
#pragma experiment("TRAITS")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import I2C
import DifferentialPair
import Resistor
import can_bridge_by_name

module TI_INA228:
    power = new ElectricPower
    i2c = new I2C
    power_in = new ElectricPower
    power_out = new ElectricPower

    shunt_input = new DifferentialPair
    shunt = new Resistor
    shunt_input.p.line ~> shunt ~> shunt_input.n.line

    power_in.hv ~> shunt ~> power_out.hv
    power_in.lv ~ power.lv
    power_out.lv ~ power.lv

    trait can_bridge_by_name<input_name="power_in", output_name="power_out">
```

### Why this is correct

- Models inline current-sense insertion physically and semantically.
- Exposes clean bridgeable interface for parent power topology.
- Separates monitor supply rail from sensed high-side path.

## 8.11 Package-derived example: USB connector chain (`usb-connectors`)

### Source-derived snippet

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")

import USB2_0
import Resistor
import can_bridge_by_name

module FusedUSB2_0:
    usb_in = new USB2_0
    usb_out = new USB2_0
    fuse = new BHFUSE_BSMD0805_050_15V_model

    usb_in.usb_if.buspower.hv ~> fuse ~> usb_out.usb_if.buspower.hv
    usb_in.usb_if.buspower.lv ~ usb_out.usb_if.buspower.lv
    usb_in.usb_if.d ~ usb_out.usb_if.d

    trait can_bridge_by_name<input_name="usb_in", output_name="usb_out">
```

### Why this is correct

- Enforces inline protection in VBUS path only.
- Preserves differential data continuity.
- Encapsulates reusable fuse bridge module.

## 8.12 Package-derived example: LED indicator bridge (`indicator-leds`)

### Source-derived snippet

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")

import LED
import Resistor
import ElectricPower
import can_bridge_by_name

module LEDIndicator:
    power = new ElectricPower
    resistor = new Resistor
    led = new LED

    current = 0.5mA to 3mA

    assert (power.voltage - led.diode.forward_voltage) / current is resistor.resistance
    assert current <= led.diode.max_current

    power.hv ~> led ~> resistor ~> power.lv

    signal low ~ power.lv
    signal high ~ power.hv
    trait can_bridge_by_name<input_name="high", output_name="low">
```

### Why this is correct

- Captures current-limiting relation explicitly.
- Exposes simple bridgeable drop-in indicator semantics.

## 8.13 Package-derived example: STM32H723 interface-rich module

### Source-derived snippet

```ato
#pragma experiment("MODULE_TEMPLATING")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")
#pragma experiment("TRAITS")

import ElectricPower
import I2C
import SPI
import UART
import USB2_0

module ST_STM32H723:
    power_3v3 = new ElectricPower
    i2c = new I2C[2]
    spi = new SPI[2]
    uart = new UART
    usb = new USB2_0

    assert power_3v3.voltage within 1.62V to 3.6V
```

### Why this is correct

- Presents scalable interface map for complex MCU.
- Keeps decoupling, crystal, and package pin map internals encapsulated.

## 8.14 Package-derived example: LAN8742A PHY (RMII+MDIO)

### Source-derived snippet

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import Ethernet

module Microchip_LAN8742A:
    power_3v3 = new ElectricPower
    rmii = new RMII
    mdio = new MDIO
    ethernet = new Ethernet

    assert power_3v3.voltage within 3.0V to 3.6V
```

### Why this is correct

- Uses dedicated interfaces for MAC and MDI domains.
- Keeps PHY-specific straps/decoupling local to module.

## 8.15 Example quality rubric

Every example in this section should satisfy:

- valid parser syntax,
- correct pragmas for used experimental features,
- explicit interfaces and references,
- meaningful constraints,
- no unsupported constructs,
- no hidden imperative assumptions.

If adapting these examples, preserve those properties first; optimize style second.

# 9. Diagnostics + Fix Playbooks

This section maps common failure classes to deterministic repair sequences.

## 9.1 Failure class: Feature not enabled (pragma gate)

### Symptom

Error indicates experiment not enabled for:

- bridge connect,
- for loop,
- trait statement,
- module templating.

### Fix playbook

1. Identify construct used (`~>`, `for`, `trait`, `new T<...>`).
2. Add corresponding pragma at top of file.
3. Keep pragma set minimal but complete.

### Example fix

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")
```

## 9.2 Failure class: Invalid import (stdlib allowlist)

### Symptom

`DslImportError` for bare `import Foo`.

### Fix playbook

1. Check if `Foo` is known stdlib allowlist entity.
2. If not, convert to path import:

```ato
from "path/to/foo.ato" import Foo
```

3. If trait alias expected, ensure correct trait name/import.

## 9.3 Failure class: Type reference assigned without `new`

### Symptom

User syntax error around assignment to type reference.

### Fix playbook

1. Replace `x = Type` with `x = new Type`.
2. If array intended, use `x = new Type[n]`.

## 9.4 Failure class: Unsupported arithmetic operator

### Symptom

Operator error for `|` or `&` in equations.

### Fix playbook

1. Replace with supported arithmetic constructs.
2. If logical intent, convert to explicit constraints or module selection pattern.

## 9.5 Failure class: Assert with multiple comparisons

### Symptom

Semantic not-implemented error for assert chain.

### Fix playbook

Split chained assert into separate asserts.

Before:

```ato
# parser accepts; semantic layer may reject
assert 1V < x < 5V
```

After:

```ato
assert x > 1V
assert x < 5V
```

## 9.6 Failure class: Unit not found

### Symptom

Unit decode error with suggestions.

### Fix playbook

1. Correct spelling/case using known symbol.
2. Prefer canonical symbols from units registry (`V`, `A`, `ohm`, `F`, `Hz`).
3. Re-check SI prefix syntax.

## 9.7 Failure class: Units not commensurable

### Symptom

Bounded/bilateral quantity unit mismatch error.

### Fix playbook

1. Verify both terms are same dimension.
2. Convert one side to commensurable unit.
3. Re-run with explicit units.

Example:

```ato
# bad
assert x within 3.3V to 5A

# good
assert x within 3.3V to 5V
```

## 9.8 Failure class: Mixed directed connect directions

### Symptom

Error: one connection direction per statement.

### Fix playbook

1. Rewrite into one direction per chain.
2. If needed, split into multiple statements with clear intermediate node.

## 9.9 Failure class: Loop body contains forbidden statement

### Symptom

Invalid statement in for loop.

### Fix playbook

1. Move forbidden statement outside loop.
2. Keep loop body to assignments/asserts/connects allowed by current rules.
3. For new child creation, pre-create sequence before loop.

## 9.10 Failure class: Undefined field/index

### Symptom

Undefined symbol or field path resolution error.

### Fix playbook

1. Verify field is declared/created before reference.
2. For indexed references, verify sequence length and index.
3. For alias-dependent paths, verify scope and loop alias names.

## 9.11 Failure class: Trait not imported / unsupported external trait

### Symptom

Trait import/type errors.

### Fix playbook

1. Import trait explicitly.
2. Verify trait is supported by allowlist or override registry.
3. If external custom trait needed, confirm pipeline support before use.

## 9.12 Failure class: Overconstrained design (contradiction)

### Symptom

Solver contradiction on parameter domains.

### Fix playbook

1. Identify all constraints on failing parameter.
2. Convert exact assignments to toleranced/bounded where acceptable.
3. Remove redundant contradictory assertions.
4. Check implicit defaults (`.default`) vs explicit assignment interactions.

## 9.13 Failure class: Underconstrained design (weak picks)

### Symptom

Unstable or poor part selection.

### Fix playbook

1. Add key electrical bounds.
2. Add package constraints for footprint policy.
3. Add manual locks for high-risk parts only.

## 9.14 Failure class: Missing references on logic/signal buses

### Symptom

Unexpected interface behavior or unresolved assumptions around line voltage domains.

### Fix playbook

1. Ensure line references point to correct rail.
2. For shared buses, align references consistently across participants.

## 9.15 Failure class: Legacy compatibility behavior confusion

### Symptom

Unexpected behavior around `reference_shim`, deprecated alias warnings, or trait alias behavior.

### Fix playbook

1. Prefer canonical explicit forms.
2. Preserve compatibility forms only when updating legacy modules without large refactors.

## 9.16 Repair sequence template

Use this sequence for most failing modules:

1. Validate pragma gates.
2. Validate imports.
3. Validate instance creation (`new`).
4. Validate connect graph (`~` vs `~>`).
5. Validate references for logic/signal buses.
6. Validate assert operator and structure.
7. Validate units and commensurability.
8. Validate picking/package overrides.
9. Re-check for under/overconstraint.

# 10. Anti-Patterns + Rewrite Recipes

## 10.1 Anti-pattern: Procedural mental model

Bad:

```ato
# implied procedural intent, not declarative constraints
# "first set x then compute y"
```

Rewrite:

- express all dependencies as equations/assertions;
- avoid order-dependent assumptions.

## 10.2 Anti-pattern: Missing pragma for experimental syntax

Bad:

```ato
a ~> b ~> c
for x in xs:
    x.package = "0402"
```

Rewrite:

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")
```

## 10.3 Anti-pattern: Type assignment without `new`

Bad:

```ato
r = Resistor
```

Rewrite:

```ato
r = new Resistor
```

## 10.4 Anti-pattern: Chain assert comparison

Bad:

```ato
assert 1V < x < 5V
```

Rewrite:

```ato
assert x > 1V
assert x < 5V
```

## 10.5 Anti-pattern: Using `is` for literal bounds

Bad:

```ato
assert v is 3.3V +/- 5%
```

Rewrite:

```ato
assert v within 3.3V +/- 5%
```

## 10.6 Anti-pattern: Bridge syntax for non-bridgable topology

Bad:

```ato
bus ~> random_module ~> sink
```

Rewrite:

- use `~` where no explicit inline bridge path is intended,
- or define appropriate bridge trait path in module.

## 10.7 Anti-pattern: Over-locking all parts early

Bad:

- hardcoding `lcsc_id` for every passive in early architecture.

Rewrite:

- constrain values/packages for passives,
- lock only critical parts initially.

## 10.8 Anti-pattern: Leaky module public API

Bad:

- exporting package-pin-level internals as parent integration contract.

Rewrite:

- expose clean interfaces (`power`, `i2c`, `spi`, `gpio`),
- keep package pin map internal.

## 10.9 Anti-pattern: Missing reference rail on logic signals

Bad:

```ato
gpio.line ~ some_line
# no reference relation
```

Rewrite:

```ato
gpio.reference ~ power
```

## 10.10 Anti-pattern: One giant monolithic module

Bad:

- power, buses, sensor math, connector mapping all in one module.

Rewrite:

- split into submodules:
  - power tree,
  - controller,
  - peripheral blocks,
  - connector adapter.

# 11. Checklists + Output Templates

## 11.1 Fast authoring checklist

- [ ] Correct block type (`module`/`interface`/`component`).
- [ ] Required pragmas declared.
- [ ] Imports valid (allowlist vs path import).
- [ ] All instances created with `new`.
- [ ] Connectivity uses `~`/`~>` appropriately.
- [ ] Logic/signal references wired.
- [ ] Constraints use `within`/`is` intentionally.
- [ ] Units/tolerances are commensurable and realistic.
- [ ] Picking/package strategy is explicit.
- [ ] No unsupported constructs used.

## 11.2 Fast review checklist

- [ ] Parser-valid syntax only.
- [ ] No semantic gate violations.
- [ ] No chain assert comparison reliance.
- [ ] No unsupported arithmetic operators.
- [ ] No unresolved field/index paths.
- [ ] No mixed bridge direction chains.
- [ ] No hidden reference-domain mistakes.
- [ ] No accidental overconstraint/underconstraint.

## 11.3 Output template: New module draft

```text
Goal:
Public interfaces:
Internal components:
Connectivity plan:
Constraint plan:
Picking/package plan:
Pragmas required:
Open risks:
```

## 11.4 Output template: Review findings

```text
Severity-ordered findings:
1) [High] ...
2) [Medium] ...
3) [Low] ...

Unsupported/experimental feature checks:
- ...

Constraint health summary:
- overconstraint risks: ...
- underconstraint risks: ...

Suggested rewrites:
- before: ...
- after: ...
```

## 11.5 Output template: Debug triage

```text
Observed error:
Likely invariant violated:
Minimal reproducer location:
Fix steps:
Validation steps:
```
