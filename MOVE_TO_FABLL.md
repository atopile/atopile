# TODO move to new fabll

- [x] GraphFunctions -> moved to Node
  - [x] replace GraphFunctions with Node.bind_typegraph
  - [x] change g to tg in GraphFunctions
- [x] Graph -> GraphView
  - [x] move to fabll
  - [x] replace with TG
  - [x] get rid of multi graphs (solver)
  - [x] Change Graph import to fabll.Graph
- [x] Module
  - [x] isinstance checks
  - [x] rename to fabll.Node
  - [x] deal with modules vs node
    - [x] get_children_modules
  - [ ] deal with specializations
- [x] ModuleInterface
  - [x] isinstance checks
  - [x] rename to fabll.Node
  - [x] replace connect_all_node_references
  - [x] implement group_into_buses
- [x] library
  - [x] inheritance from Module/Node/Trait/ModuleInterface
  - [x] libs/L.py
  - [x] use new fabll
- [ ] Traits
  - [ ] for usage change constructor call to setup()
  - [ ] refactor all traits
  - [ ] replace <node>.add(<trait>) with Traits.add_to(<node>, <trait>)
  - [ ] replace all trait inits `<trait>()`
  - [ ] handle_duplicate
  - [ ] on_obj_set
- [x] Parameter
  - [x] literals (fabll.Range...)
- [x] Links
- [x] GraphInterface
- [x] CNode

- [ ] Move all faebryk pyis into faebryk.pyi
- [x] Figure out how to convert ChildField to instance
- [ ] composition name optional? (currently id() hack)

SOLVER:

- [x] use F imports
- [x] think and fix Graph handling in mutator
- [x] check for `type` and `isinstance` and `cast`
- [ ] consider renaming parameter_operatable to something shorter and better (now that we have operand)
- [x] fix type errors in all algos
  - [x] canonical
  - [x] expression_groups
  - [x] expression_wise
  - [x] pure_literal
  - [x] structural
- [x] check for sibling trait, cast, get_trait, and get_raw_obj
- [ ] reconsider using is_canonical

##

- node.get_children

## Strategy

## Notes

- rename node.py to fabll.py
- use graph.py as graph
- use faebrykpy.py as fbrk (consider renaming to fbrk)

## TESTS

expr_factory

- temp hack: just save tg->fabll dict somewhere in node
- later solution, make is_expression function that can build automatically
  - for that just move lhs, rhs, other operand sets into is_expression and point to them from top node

solver todo

- [ ] mark exprs as literal during expr_mutation, then flag to solver that it needs to run flatten_literals afterwards

NOTE TO SELF FRIDAY

- currently going through `test_solver.py`
- running `./test/runpytesttable.sh -m "not slow" test/core/solver/test_solver.py`
  and then checking test-report.html
- got rid of (almost all) superficial errors
  - now only slow / contradiction / assert result errors (actual solver errors) left
    - fix last superficial error, then slowly start going one-by-one through solver errors
      (might want to first focus on the lit folding to make sure)

```
 20 × AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative_2 - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_r_top - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_with_division - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_in - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_resistor - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_param_isolation - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_abstract_lowpass - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_simple_parameter_isolation - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_literals - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_resistances - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_subtract_zero[c0] - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_single_variable_occurrences - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_not - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_capacitor - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_subtract_zero[c1] - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_nested_fold_interval - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_or_true - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_no_division - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_canonical_subtract_zero - AssertionError: assert False

  4 × Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_obvious_contradiction_by_literal - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_domain - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_subset_is - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_voltage_divider_reject_invalid_r_top - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>

  4 × assert None is not None
    FAILED test/core/solver/test_solver.py::test_shortcircuit_logic_or - assert None is not None
    FAILED test/core/solver/test_solver.py::test_very_simple_alias_class - assert None is not None
    FAILED test/core/solver/test_solver.py::test_base_unit_switch - assert None is not None
    FAILED test/core/solver/test_solver.py::test_fold_pow - assert None is not None

  3 × AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[10] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[5] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[15] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'

  2 × faebryk.core.solver.utils.ContradictionByLiteral: Contradiction: Tried alias to different literal
    FAILED test/core/solver/test_solver.py::test_congruence_filter - faebryk.core.solver.utils.ContradictionByLiteral: Contradiction: Tried alias to different literal
    FAILED test/core/solver/test_solver.py::test_empty_and - faebryk.core.solver.utils.ContradictionByLiteral: Contradiction: Tried alias to different literal

  1 × AssertionError: assert False is True
    FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected3] - AssertionError: assert False is True

  1 × NotImplementedError: Resuming state not supported yet in new core
    FAILED test/core/solver/test_solver.py::test_simplify_non_terminal_manual_test_1 - NotImplementedError: Resuming state not supported yet in new core

  1 × NotImplementedError: domain_set not implemented for EnumParameter
    FAILED test/core/solver/test_solver.py::test_simple_pick - NotImplementedError: domain_set not implemented for EnumParameter

  1 × NotImplementedError: op_intersect_intervals not implemented for AbstractEnums
    FAILED test/core/solver/test_solver.py::test_simple_negative_pick - NotImplementedError: op_intersect_intervals not implemented for AbstractEnums

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Literals.is_literal'> found on <Node[NumericParameter] '0x...)'>
    FAILED test/core/solver/test_solver.py::test_symmetric_inequality_correlated - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Literals.is_literal'> found on <Node[NumericParameter] '0x55EE0ABD9B20)'>

  1 × faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x....is_assertable)' on <Node[IsSubset] '0x...)'>>
    FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[IsSubset] - faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x55936B6A3720.is_assertable)' on <Node[IsSubset] '0x55936B6A3720)'>>

  1 × faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x....is_assertable)' on <Node[Is] '0x...)'>>
    FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[Is] - faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x55B6D230BCB0.is_assertable)' on <Node[Is] '0x55B6D230BCB0)'>>

  1 × faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x....is_assertable)' on <Node[Not] '0x...)'>>
    FAILED test/core/solver/test_solver.py::test_deduce_negative - faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x559FFD2CD0F0.is_assertable)' on <Node[Not] '0x559FFD2CD0F0)'>>

  1 × faebryk.core.solver.utils.ContradictionByLiteral: Contradiction: Intersection of literals is empty
    FAILED test/core/solver/test_solver.py::test_implication - faebryk.core.solver.utils.ContradictionByLiteral: Contradiction: Intersection of literals is empty
```
