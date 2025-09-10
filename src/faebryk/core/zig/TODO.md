justify/alignment: TEST
TextLayer(knockout)
layer/layers in geo

test checksum
| i think the lib fp checksum will make all boards components lose their position

visit_dataclass
filter_fields

layout_reuse

refactor encode to let bottom type build list (with name) instead of struct
[or in other words, invariant that root type is a struct]

# TESTS

## Solver

FAILED test/core/solver/test_literal_folding.py::test_can_evaluate_literals - decimal.InvalidOperation: [<class 'decimal.InvalidOperation'>]
FAILED test/core/solver/test_literal_folding.py::test_discover_literal_folding - AssertionError: Mismatch ([0]) != ([1e-12, ∞])
FAILED test/core/performance/test_performance_pick.py::test_performance_pick_real_module[RP2040_ReferenceDesign] - faebryk.libs.picker.picker.PickError: Contradiction: Tried subset to different literal
FAILED test/core/solver/test_solver.py::test_solve_realworld_biggest - faebryk.libs.picker.picker.PickError: Contradiction: Tried subset to different literal
FAILED test/libs/picker/test_pickers.py::test_pick_dependency_advanced_1 - faebryk.libs.picker.picker.PickVerificationError: Post-pick verification failed for picked parts:

## Regressions

FAILED test/test_regressions.py::test_projects[https://github.com/atopile/spin-servo-drive] - test.test_regressions.CloneError
FAILED test/test_regressions.py::test_projects[https://github.com/atopile/packages] - test.test_regressions.CloneError

## Actual

FAILED test/end_to_end/test_net_name_determinism.py::test_net_names_deterministic - AssertionError: [12:11:31] WARNING Your version of atopile (0.12.1) is out-of-date. Latest version: 0.12.4....

FAILED test/test_examples.py::test_examples_build[esp32_minimal] - AssertionError: assert 2 in (0, 1)
