# Hackathon: Solver 100x speed 🚀

**$4k prize - 6-10pm PST, Wed 17-Feb, Stanford (TBD)**

​Judged on solver speed, with bonus points for solving complex equations.

​A perfect SMT solver isn't magic—it's the ultimate code hack that transforms bugs and bottlenecks into well-formed, elegant solutions. However, since perfect solvers don't exist, we at atopile built our own.

​While software lives in an ideal world, the real world is fuzzy—you never have exact values, and tolerances always matter. Traditional CAS/SMT solvers struggle with this fuzziness, their performance degrading to O(N!). That's why we created our own solver for the atopile circuit board compiler. If you succeed in improving it, we'll include your work in the atopile compiler (MIT licensed).

​Resources:

- [atopile solver introduction](https://github.com/atopile/atopile/tree/main/src/faebryk/core/solver)
- [Z3](https://github.com/Z3Prover/z3) is Microsoft's SMT solver, used in compilers for typing
- [SAT_SMT_by_example](https://smt.st/SAT_SMT_by_example.pdf) (PDF/book) formal SMT solver docs


## Rules

- no new libraries or external tools (unless approved by organizers)
- code must be in python or c++ (hint; we don't expect much over a 2x speedup going out of python)
- all passing tests need to remain passing
- even if all tests pass, doing something obviously incorrect will result in a penalty
- if picker accepts invalid parts, solver will be considered incorrect
- minimum points required: 100


## Point system
The points are cumulative.

- Speeding up benchmark
    - from 2x: 100 points
    - from 5x: another 100 points
    - from 10x: another 100 points
    - from 20x: another 100 points
    - from 50x: another 100 points
    - from 100x: another 100 points (total 600)
- Finding (functional) bugs
    - non solver test bug: 5 points
    - library bug: 10 points
    - solver test bug: 15 points
    - mutator bug: 20 points
    - math bug: 30 points
- Bonus points
    - Speeding up non-solver/picker related code: 10 - 200 points
    - Extending solver capabilities: 10 - 300 points

## Getting started

1. Clone & setup [atopile](https://github.com/atopile/atopile)
2. Read the [atopile solver introduction](https://github.com/atopile/atopile/tree/main/src/faebryk/core/solver)
3. Run the solver functional test suite

```bash
pytest test/core/solver/test_solver.py
```

4. Run the literal folding fuzzer regression tests

```bash
./test/runpytest.sh -k test_regression_literal_folding
```

5. Run the literal folding fuzzer statistics

```bash
FBRK_ST_NUMEXAMPLES=1000 FBRK_STIMEOUT=2 FBRK_SPARTIAL=n ./test/runpytest.sh -Wignore --hypothesis-show-statistics -k "test_folding_statistics" | grep -v Retried | grep -v "invalid because"
```
6. Run the solver benchmark
```bash
python ./test/runtest.py -k "test_performance_pick_rc_formulas"
```
7. Get to work

## Pointers

### Algorithmic: Picker - [picker.py](../../src/faebryk/libs/picker/picker.py):pick_topologically
The solver itself is not super slow, but it's called a lot during picking.
There are ways to reduce the number of solver calls.

- picking parts by solver instead of looping through candidates
- picking parts in smarter sequences (e.g sort by parameter variance)
- picking parts in parallel, by finding independent module groups

### Implementation: Mutator - [mutator.py](../../src/faebryk/core/solver/mutator.py)
Mutation by copy is very expensive if done for large graphs.

- improve `Expression`/`Parameter` construction speed
- avoid graph copies if not necessary
- switch to mutable graph for intermediate stages of solver

### Mathematical: Solver - [analytical.py](../../src/faebryk/core/solver/analytical.py)
Every solver algorithm/iteration costs time.
If algorithms can reach most strong expressions faster, fewer iterations are needed.
If results can be shared between solver runs, even better.

- split `destructive` algorithms from `non-destructive` algorithms
- avoid creating or checking too often for duplicate expressions


## Handy environment variables

- `FBRK_STIMEOUT`: timeout for solver
- `FBRK_SPARTIAL`: allow using solver results despite timeout
- `FBRK_LOG_PICK_SOLVE`: some extra verbosity for picking and solving logs
- `FBRK_LOG_FMT`: math expression highlighting and stack traces
- `FBRK_SLOG`: very detailed mathematical expression logging
- `FBRK_SMAX_ITERATIONS`: maximum iterations for solver

## Profiling
Have a look in [profile.py](../../tools/profile.py) for tools to profile the solver.
Also useful for in-code instrumenting: [times.py](../../src/faebryk/libs/test/times.py)