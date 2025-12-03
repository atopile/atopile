# TODO move to new fabll

- [x] GraphFunctions -> moved to Node
  - [x] replace GraphFunctions with Node.bind_typegraph
  - [x] change g to tg in GraphFunctions
- [ ] Graph -> GraphView
  - [x] move to fabll
  - [x] replace with TG
  - [ ] get rid of multi graphs (solver)
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
- [ ] library
  - [x] inheritance from Module/Node/Trait/ModuleInterface
  - [x] libs/L.py
  - [ ] use new fabll
- [ ] Traits
  - [ ] for usage change constructor call to setup()
  - [ ] refactor all traits
  - [ ] replace <node>.add(<trait>) with Traits.add_to(<node>, <trait>)
  - [ ] replace all trait inits `<trait>()`
  - [ ] handle_duplicate
- [ ] Parameter
  - [ ] literals (fabll.Range...)
- [ ] Links
- [ ] GraphInterface
- [ ] CNode

- [ ] Move all faebryk pyis into faebryk.pyi
- [ ] Figure out how to convert ChildField to instance
- [ ] composition name optional? (currently id() hack)

SOLVER:

- [ ] use F imports
- [ ] think and fix Graph handling in mutator
- [ ] check for `type` and `isinstance` and `cast`
- [ ] consider renaming parameter_operatable to something shorter and better (now that we have operand)
- [WIP, revisit after util] fix type errors in all algos
  - [x] canonical
  - [x] expression_groups
  - [x] expression_wise
  - [x] pure_literal
  - [x] structural
- [ ] check for sibling trait, cast, get_trait, and get_raw_obj
- [ ] reconsider using is_canonical

##

- node.get_children

## Strategy

## Notes

- rename node.py to fabll.py
- use graph.py as graph
- use faebrykpy.py as fbrk (consider renaming to fbrk)

## TESTS

==== 275 failed, 545 passed, 6 skipped, 46 xfailed, 1 xpassed, 50 warnings, 17 errors in 26.08s =====

NOTE TO SElF

currently busy prepping mutator for new G semantics

- changed identity def to bootstrap
- created an empty G_out in mutator
  strat: continue in mutator close/copy_unmutated etc to see how we can copy this

another challenge coming up is getting the expr_factory setup from just an instance

- temp hack: just save tg->fabll dict somewhere in node
- later solution, make is_expression function that can build automatically
  - for that just move lhs, rhs, other operand sets into is_expression and point to them from top node

Be careful with modifying G_in on first stage, modifying source graph

- e.g predicate terminatation. safest is to copy on first stage

BIG TODO: check everywhere for `==` in solver
also `in`
=> had a first pass

NOTE TO SELF THURSDAY:

- something wrong with bool subset vs alias in our test
- stuff is very slow still (but not due to tg anymore)
- still a bunch of lit & param stuff not implemented
- get_trait creates lots of runtime problems, switch to \_trait.get()
  - consider invariant field in traits to capture sibling relationship
- pure literal seems a bit fucked (operand order)

NOTE TO SELF TUESDAY:

- started fixing solver stuff for numeric parameters
- was fixing test_simplify in test_solver.py
  - now working, but hangs/slow?
- ran pytest in the evening, but will take a while
  - check on it in morning

solver todo

- [ ] segfault at merge_parameters (>5x)

```
  File "/home/needspeed/workspace/atopile/src/faebryk/core/node.py", line 1461 in connect
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Collections.py", line 86 in point
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Parameters.py", line 589 in setup
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/utils.py", line 1158 in merge_parameters
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/symbolic/structural.py", line 306 in resolve_alias_classes
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/algorithm.py", line 51 in wrapped
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/algorithm.py", line 24 in __call__
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/mutator.py", line 1909 in _run
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/defaultsolver.py", line 154 in _run_iteration
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/defaultsolver.py", line 398 in simplify_symbolically
  File "/home/needspeed/workspace/atopile/src/faebryk/libs/util.py", line 1931 in wrapper
  File "/home/needspeed/workspace/atopile/test/core/solver/test_solver.py", line 656 in test_alias_classes
```

- [ ] Other segfault (1 occurence)

```
  File "/home/needspeed/workspace/atopile/src/faebryk/core/node.py", line 1461 in connect
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Collections.py", line 86 in point
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Units.py", line 667 in setup
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Literals.py", line 2485 in setup
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Literals.py", line 2747 in convert_to_unit
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Literals.py", line 2760 in _convert_other_to_self_unit
  File "/home/needspeed/workspace/atopile/src/faebryk/library/Literals.py", line 2805 in op_add_intervals
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/symbolic/expression_wise.py", line 151 in <lambda>
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/utils.py", line 731 in fold_op
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/symbolic/expression_wise.py", line 149 in fold_add
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/symbolic/expression_wise.py", line 65 in fold_literals
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/symbolic/expression_wise.py", line 101 in wrapped
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/algorithm.py", line 51 in wrapped
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/algorithm.py", line 24 in __call__
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/mutator.py", line 1909 in _run
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/defaultsolver.py", line 154 in _run_iteration
  File "/home/needspeed/workspace/atopile/src/faebryk/core/solver/defaultsolver.py", line 398 in simplify_symbolically
  File "/home/needspeed/workspace/atopile/src/faebryk/libs/util.py", line 1931 in wrapper
  File "/home/needspeed/workspace/atopile/test/core/solver/test_solver.py", line 1009 in test_literal_folding_add_multiplicative_2
```

```
FAILED test/core/solver/test_solver.py::test_transitive_subset - AssertionError: SEGFAULTING
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands4-50] - AssertionError: assert None == 50
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands0-15] - AssertionError: assert None == 15
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands2-15] - AssertionError: assert None == 15
FAILED test/core/solver/test_solver.py::test_shortcircuit_logic_and - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands5-0.5] - AssertionError: assert None == 0.5
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands1-10] - AssertionError: assert None == 10
FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands3--5] - AssertionError: assert None == -5
FAILED test/core/solver/test_solver.py::test_subset_single_alias - AttributeError: 'NoneType' object has no attribute 'is_empty'
FAILED test/core/solver/test_solver.py::test_domain - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_shortcircuit_logic_or - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_assertable'> found
FAILED test/core/solver/test_solver.py::test_base_unit_switch - TypeError: Numbers.max_elem() missing 2 required positional arguments: 'g' and 'tg'
FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[IsSubset] - AttributeError: 'NoneType' object has no attribute 'is_empty'
FAILED test/core/solver/test_solver.py::test_inequality_to_set - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_inspect_enum_simple - ValueError: Cannot cast literal <is_literal '0x555A857000B0.is_literal)' on <Node[Color] '0x555A857000B0)'>> of type <Node[Color] ...
FAILED test/core/solver/test_solver.py::test_combined_add_and_multiply_with_ranges - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_capacitor - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_congruence_filter - ValueError: Cannot cast literal <is_literal '0x564E751248A0.is_literal)' on <Node[Color] '0x564E751248A0)'>> of type <Node[Color] ...
FAILED test/core/solver/test_solver.py::test_simple_negative_pick - AttributeError: module 'faebryk.library.Parameters' has no attribute 'bind_typegraph'
FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[Is] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_remove_obvious_tautologies - StopIteration
FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_resistor - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_nested_additions - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_with_division - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_simple_parameter_isolation - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found
FAILED test/core/solver/test_solver.py::test_less_obvious_contradiction_by_literal - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_no_division - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_subset_is
FAILED test/core/solver/test_solver.py::test_symmetric_inequality_correlated
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-True0] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-True1] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_subset_of_literal
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_r_top - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-False1] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_solve_phase_one
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-True2] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-True3] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_inspect_enum_led - ValueError: Cannot cast literal <is_literal '0x55BC962779D0.is_literal)' on <Node[Color] '0x55BC962779D0)'>> of type <Node[Color] ...
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-False3] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-False0] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c1] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_very_simple_alias_class
FAILED test/core/solver/test_solver.py::test_param_isolation - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found
FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c2] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_abstract_lowpass - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative_2
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_gt - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_in - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_ss_single_into_alias - AttributeError: 'NoneType' object has no attribute 'is_empty'
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_single_variable_occurrences - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_can_add_parameters - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_fold_not - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_ss_estimation_ge - AttributeError: 'NoneType' object has no attribute 'is_empty'
FAILED test/core/solver/test_solver.py::test_fold_pow - TypeError: Invalid type: <class 'NoneType'>
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected4] - AssertionError: assert False == True
FAILED test/core/solver/test_solver.py::test_fold_ss_transitive - AssertionError: SEGFAULTING
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected6] - TypeError: Numbers.equals() missing 2 required positional arguments: 'tg' and 'other'
FAILED test/core/solver/test_solver.py::test_empty_and - ValueError: At least one operand is required
FAILED test/core/solver/test_solver.py::test_mapping[5] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c3] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_mapping[15] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
FAILED test/core/solver/test_solver.py::test_deduce_negative - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_voltage_divider_reject_invalid_r_top - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
FAILED test/core/solver/test_solver.py::test_implication - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.can_be_operand'> found
FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c0] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-False2] - AttributeError: 'can_be_operand' object has no attribute 'assert_'
FAILED test/core/solver/test_solver.py::test_ss_intersect - AssertionError: SEGFAULTING
FAILED test/core/solver/test_solver.py::test_fold_literals - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_mapping[10] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
FAILED test/core/solver/test_solver.py::test_subtract_zero[c0] - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_nested_fold_scalar - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_regression_lit_mul_fold_powers - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_simplify_non_terminal_manual_test_1 - NotImplementedError: Resuming state not supported yet in new core
FAILED test/core/solver/test_solver.py::test_fold_mul_zero - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_fold_or_true - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>1] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55BCA1DDFE20)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected0] - TypeError: Numbers.equals() missing 2 required positional arguments: 'tg' and 'other'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>2] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55BCA1FE7F80)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>4] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x560BEDE1A110)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected2] - TypeError: Numbers.equals() missing 2 required positional arguments: 'tg' and 'other'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>12] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected1] - TypeError: Numbers.equals() missing 2 required positional arguments: 'tg' and 'other'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>6] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>5] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x560BEE035B00)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>13] - faebryk.core.node.FabLLException: Node <Node[Booleans] '0x555A72258D20)'> is not an instance of <class 'faebryk.library.Parameters...
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>14] - AttributeError: 'NoneType' object has no attribute 'instance'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>7] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x5628DA833910)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>15] - ValueError: At least one operand is required
FAILED test/core/solver/test_solver.py::test_nested_fold_interval - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected3] - TypeError: Numbers.equals() missing 2 required positional arguments: 'tg' and 'other'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>18] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>17] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>20] - TypeError: BoundExpressions.lit_op_range() takes 2 positional arguments but 3 were given
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>19] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>16] - faebryk.core.node.FabLLException: Node <Node[Booleans] '0x5618CF839C50)'> is not an instance of <class 'faebryk.library.Parameters...
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>21] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>24] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_canonical_subtract_zero - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>22] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>26] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>23] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_subtract_zero[c1] - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>3] - ValueError: At least one operand is required
FAILED test/core/solver/test_solver.py::test_simplify_logic_and - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_canonical'> found
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>8] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_regression_enum_contradiction - ValueError: Cannot cast literal <is_literal '0x5618CFAB2320.is_literal)' on <Node[Color] '0x5618CFAB2320)'>> of type <Node[Color] ...
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>9] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55A8898DBE90)'> is not an instance of <class 'faebryk.library.Parameters....
FAILED test/core/solver/test_solver.py::test_voltage_divider_find_resistances - AttributeError: 'is_literal' object has no attribute 'is_superset_of'. Did you mean: 'is_subset_of'?
FAILED test/core/solver/test_solver.py::test_subset_is_expr - AttributeError: 'is_literal' object has no attribute 'is_superset_of'. Did you mean: 'is_subset_of'?
FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected5] - AssertionError: assert False == True
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>10] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>11] - IndexError: list index out of range
FAILED test/core/solver/test_solver.py::test_simple_pick - AttributeError: module 'faebryk.library.Parameters' has no attribute 'bind_typegraph'
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>25] - AttributeError: 'NoneType' object has no attribute 'tg'
FAILED test/core/solver/test_solver.py::test_simple_literal_folds_arithmetic[c-operands0-15] - AssertionError: assert False
FAILED test/core/solver/test_solver.py::test_graph_split
FAILED test/core/solver/test_solver.py::test_exec_pure_literal_expressions[<lambda>-<lambda>-<lambda>0] - ValueError: At least one operand is required
FAILED test/core/solver/test_solver.py::test_alias_classes
FAILED test/core/solver/test_solver.py::test_inspect_known_superranges - TypeError: '_LazyProxy' object is not callable
FAILED test/core/solver/test_solver.py::test_obvious_contradiction_by_literal
FAILED test/core/solver/test_solver.py::test_simplify_non_terminal_manual_test_2 - TimeoutError: Function simplify_symbolically exceeded time limit of 150s
FAILED test/core/solver/test_solver.py::test_fold_correlated - AssertionError: assert False
======================================== 123 failed, 2 passed, 8 xfailed in 164.82s (0:02:44) =========================================
```
