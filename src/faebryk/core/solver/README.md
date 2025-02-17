# :alembic: Rum is technically a solution

> The solver doesn't bite, but it will hurt you in different ways. - Ioannis P

## Overview of the parameter subsystem

- literals - `Sets` - [libs/sets](../../libs/sets)
    - `Numeric`, `Quantities`
    - `Boolean`
    - `Enums` 
- correlation in set algebra
    - literal correlation
    - `Expression` congruency
- symbols - `ParameterOperatables` - [core/parameter.py](../../core/parameter.py)
    - `Parameters`
    - `Expressions`
    - `ConstrainableExpressions`
- data structures
    - `Expression` trees
    - the `Graph` - [core/cpp/graph api](../../core/cpp/__init__.pyi)
    - `Mutator` - [core/solver/mutator.py](../solver/mutator.py)
- canonicalization
- solving - [core/solver](../..//core/solver)
    - computer algebra - symbolic solving
    - constraint solving
    - numerical solving: WIP
- picking parts - [libs/picker.py](../../libs/picker/picker.py)
- optimization: WIP

### Introduction
We are using parameters to express some form of attribute of a module that is within the numeric, boolean or enum domain. Think of a very simple resistor
```ato
# ato
module Resistor:
    resistance: Ohm
    rated_power: W
```
```python
# fab ll
class Resistor(Module):
    resistance = L.p_field(
        unit=P.Ohm, 
        domain=L.Domains.Numbers.REAL(negative=False),
    )
    rated_power = L.p_field(
        unit=P.W,
        domain=L.Domains.Numbers.REAL(negative=False),
    )
```
What sets parameters apart from construction arguments is their ability to be defined at a *later time* and *implicitly through a set of constraints*.

```ato
psu = new PowerSupply
resistor = new Resistor
assert resistor.resistance within 100kOhm +/- 10%
assert resistor.rated_power >= psu.voltage * psu.max_current
```

These assertions not only ensure that the design is consistent but it also communicates relationships and constrains to the core. Those can be then used to automatically pick parts for modules that have no explicit parts defined.

#### Literals

You might have noticed that in the example above we used the syntax `100kOhm +/- 10%` to express that the resistance has to be within a certain range. This is a very typical way to denote values in atopile because most things in the real world are not exact. This can be due to manufacturing tolerances or fluctuations caused by unpredicatable external factors (e.g temperature).
*Important: Make sure that all parameters live in the same environment:
e.g is the voltage of a `5V +/-10%` power supply a subset of `4.5V` to `5.5V` or a subset of `0V` to `5.5V` because the power supply might be off that fully depends on the perspective (environment) of a design. Most often one should choose for the most general case which would include the ramping up from 0V to the nominal voltage. But in real a lot of engineering is done around a specific fixpoint/state of a system to optimize engineering time.*

We call those non-variable containing values **literals**.
They are represented as `Sets`. `100kOhm +/- 10%` is just a set that contains all real numbers between `90e3` and `110e3` with a unit of `Ohm`. Sets are thus more general than intervals or singletons (`100kOhm` exactly). 
Literals are in the most cases some form of set of real numbers with a unit, but we also support sets of booleans and enums.

```python
class Capacitor(Module):
    class TemperatureCoefficient(Enum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    temperature_coefficient = L.p_field(
        domain=L.Domains.ENUM(TemperatureCoefficient),
    )

```

We can do arithmetic with literals
```python
Range(100*P.W, 200*P.W) * 2
-> Range(200*P.W, 400*P.W)

Range(100*P.W, 200*P.W) + 10*P.W
-> Range(110*P.W, 210*P.W)

Range(100*P.W, 200*P.W) + Range(10*P.W, 20*P.W)
-> Range(110*P.W, 220*P.W)
```

Let's take a second to have a closer look at the last example.
Apparently if you add two intervals (special case of sets) you get a new interval that covers all possible values of the two sets. This is the case for any operation between two sets.


$$ 
\begin{aligned}
    \forall S \in \mathcal{P}, \forall X,Y \subseteq S, f: S \times S \to S : f(X,Y) := \{ f(x,y) \mid x \in X, y \in Y \}
\end{aligned}
$$
*In simple words: We define an elementwise function applied to sets as the set of all combinations of the function applied to any element of the first set and any element of the second set.*
Note: This extends also beyond the Real domain.

This definition brings us to an interesting case:

```python
X = Range(10*P.W, 20*P.W)
X - X
-> Range(-10*P.W, 10*P.W)
```

But:
```python
X = Range(10*P.W, 10*P.W) # aka Single(10*P.W)
X - X
-> Range(0*P.W, 0*P.W) # aka Single(0*P.W)
```

Basically, our definition results in:
> Singletons are auto-correlated
> Every other set is fully uncorrelated to any other set

And since our literals are all sets, any literal is uncorrelated to itself.

There are some interesting patterns in set arithmetic that we won't go into here.
But good to see an example:
```python
Range(10, 20) / Range(-1, 1)
-> Range(-10, inf) # due to lim(y->0) (x/y) = inf
```

#### Symbols

Well, so how can we express correlations then?
```python
X = Range(10*P.W, 20*P.W)
A = Parameter()
A.alias_is(X)
E = A - A
out, = DefaultSolver().simplify_symbolically(E)
out[E]
-> Single(0*P.W)

```

A lot is happening here, but the important bit is our symbols or as we call them `ParameterOperatables`. Here the more specific `Parameters` (A in this example) and `Expressions` (E in this example).
Parameters are very closely related to how we think of variables in math, but not variables in programming.
Expressions are a tuple of an operation and a list of operands. Operands can be literal or ParameterOperatables.