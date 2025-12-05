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

- [ ] mark exprs as literal during expr_mutation, then flag to solver that it needs to run flatten_literals afterwards

```
        14 × AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_resistor - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_in - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_with_division - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_capacitor - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_not - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_param_isolation - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_literals - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_subtract_zero[c1] - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_simple_parameter_isolation - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_no_division - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_nested_fold_interval - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_v_out_single_variable_occurrences - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_canonical_subtract_zero - AssertionError: assert False
    FAILED test/core/solver/test_solver.py::test_fold_or_true - AssertionError: assert False

  4 × ValueError: incompatible units
    FAILED test/core/solver/test_solver.py::test_subset_single_alias - ValueError: incompatible units
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_r_top - ValueError: incompatible units
    FAILED test/core/solver/test_solver.py::test_abstract_lowpass - ValueError: incompatible units
    FAILED test/core/solver/test_solver.py::test_voltage_divider_find_resistances - ValueError: incompatible units

  3 × AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[5] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[10] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'
    FAILED test/core/solver/test_solver.py::test_mapping[15] - AttributeError: 'NumericParameter' object has no attribute 'constrain_mapping'

  2 × AttributeError: module 'faebryk.library.Parameters' has no attribute 'bind_typegraph'
    FAILED test/core/solver/test_solver.py::test_simple_pick - AttributeError: module 'faebryk.library.Parameters' has no attribute 'bind_typegraph'
    FAILED test/core/solver/test_solver.py::test_simple_negative_pick - AttributeError: module 'faebryk.library.Parameters' has no attribute 'bind_typegraph'

  2 × Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_domain - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>
    FAILED test/core/solver/test_solver.py::test_voltage_divider_reject_invalid_r_top - Failed: DID NOT RAISE <class 'faebryk.core.solver.utils.ContradictionByLiteral'>

  2 × TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
    FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative - TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
    FAILED test/core/solver/test_solver.py::test_literal_folding_add_multiplicative_2 - TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'

  1 × AssertionError: assert False is True
    FAILED test/core/solver/test_solver.py::test_congruence_lits[<lambda>-<lambda>-expected3] - AssertionError: assert False is True

  1 × NotImplementedError: Resuming state not supported yet in new core
    FAILED test/core/solver/test_solver.py::test_simplify_non_terminal_manual_test_1 - NotImplementedError: Resuming state not supported yet in new core

  1 × ValueError: Cannot cast literal <is_literal '0x556B9E87E3F0.is_literal)' on <Node[Color] '0x556B9E87E3F0)'>> of type <Node[Color] '0x556B9E87E3F0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]
    FAILED test/core/solver/test_solver.py::test_inspect_enum_led - ValueError: Cannot cast literal <is_literal '0x556B9E87E3F0.is_literal)' on <Node[Color] '0x556B9E87E3F0)'>> of type <Node[Color] '0x556B9E87E3F0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]

  1 × ValueError: Cannot cast literal <is_literal '0x558366F868B0.is_literal)' on <Node[Color] '0x558366F868B0)'>> of type <Node[Color] '0x558366F868B0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]
    FAILED test/core/solver/test_solver.py::test_inspect_enum_simple - ValueError: Cannot cast literal <is_literal '0x558366F868B0.is_literal)' on <Node[Color] '0x558366F868B0)'>> of type <Node[Color] '0x558366F868B0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]

  1 × ValueError: Cannot cast literal <is_literal '0x55B1F746CDE0.is_literal)' on <Node[Color] '0x55B1F746CDE0)'>> of type <Node[Color] '0x55B1F746CDE0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]
    FAILED test/core/solver/test_solver.py::test_congruence_filter - ValueError: Cannot cast literal <is_literal '0x55B1F746CDE0.is_literal)' on <Node[Color] '0x55B1F746CDE0)'>> of type <Node[Color] '0x55B1F746CDE0)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]

  1 × ValueError: Cannot cast literal <is_literal '0x55E342D51D60.is_literal)' on <Node[Color] '0x55E342D51D60)'>> of type <Node[Color] '0x55E342D51D60)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]
    FAILED test/core/solver/test_solver.py::test_regression_enum_contradiction - ValueError: Cannot cast literal <is_literal '0x55E342D51D60.is_literal)' on <Node[Color] '0x55E342D51D60)'>> of type <Node[Color] '0x55E342D51D60)'> to any of [<class 'faebryk.library.Literals.Strings'>, <class 'faebryk.library.Literals.Numbers'>, <class 'faebryk.library.Literals.Booleans'>, <class 'faebryk.library.Literals.AbstractEnums'>]

  1 × assert None is not None
    FAILED test/core/solver/test_solver.py::test_fold_pow - assert None is not None

  1 × faebryk.core.node.FabLLException: Node <Node[Booleans] '0x55FE0F065120)'> is not an instance of <class 'faebryk.library.Expressions.Not'>
    FAILED test/core/solver/test_solver.py::test_shortcircuit_logic_and - faebryk.core.node.FabLLException: Node <Node[Booleans] '0x55FE0F065120)'> is not an instance of <class 'faebryk.library.Expressions.Not'>

  1 × faebryk.core.node.FabLLException: Node <Node[Booleans] '0x5647D86EA330)'> is not an instance of <class 'faebryk.library.Expressions.Or'>
    FAILED test/core/solver/test_solver.py::test_empty_and - faebryk.core.node.FabLLException: Node <Node[Booleans] '0x5647D86EA330)'> is not an instance of <class 'faebryk.library.Expressions.Or'>

  1 × faebryk.core.node.FabLLException: Node <Node[Numbers] '0x556BA1107150)'> is not an instance of <class 'faebryk.library.Expressions.Power'>
    FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c3] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x556BA1107150)'> is not an instance of <class 'faebryk.library.Expressions.Power'>

  1 × faebryk.core.node.FabLLException: Node <Node[Numbers] '0x558361C92260)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>
    FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands3--5] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x558361C92260)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>

  1 × faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55DA6387DA60)'> is not an instance of <class 'faebryk.library.Expressions.Power'>
    FAILED test/core/solver/test_solver.py::test_super_simple_literal_folding[c-operands5-0.5] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55DA6387DA60)'> is not an instance of <class 'faebryk.library.Expressions.Power'>

  1 × faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55FE1D75A910)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>
    FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c2] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x55FE1D75A910)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>

  1 × faebryk.core.node.FabLLException: Node <Node[Numbers] '0x5625562AA820)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>
    FAILED test/core/solver/test_solver.py::test_subtract_zero[c0] - faebryk.core.node.FabLLException: Node <Node[Numbers] '0x5625562AA820)'> is not an instance of <class 'faebryk.library.Expressions.Multiply'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_assertable'> found on <Node[BooleanParameter] '0x5647C173D9B0)'>
    FAILED test/core/solver/test_solver.py::test_shortcircuit_logic_or - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_assertable'> found on <Node[BooleanParameter] '0x5647C173D9B0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found on <Node[BooleanParameter] '0x5583719FE060)'>
    FAILED test/core/solver/test_solver.py::test_deduce_negative - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Expressions.is_expression'> found on <Node[BooleanParameter] '0x5583719FE060)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter'> found on <Node[Add] '0x56449A0F1F00)'>
    FAILED test/core/solver/test_solver.py::test_can_add_parameters - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter'> found on <Node[Add] '0x56449A0F1F00)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5567D59725F0)'>
    FAILED test/core/solver/test_solver.py::test_very_simple_alias_class - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5567D59725F0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5567E2F748F0)'>
    FAILED test/core/solver/test_solver.py::test_ss_estimation_ge - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5567E2F748F0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x556B97F2A130)'>
    FAILED test/core/solver/test_solver.py::test_subset_is - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x556B97F2A130)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x556BA9E8C5F0)'>
    FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-False1] - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x556BA9E8C5F0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55836E3A9490)'>
    FAILED test/core/solver/test_solver.py::test_find_contradiction_by_predicate[c-True1] - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55836E3A9490)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55B1EF028550)'>
    FAILED test/core/solver/test_solver.py::test_less_obvious_contradiction_by_literal - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55B1EF028550)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55B1F952D1E0)'>
    FAILED test/core/solver/test_solver.py::test_fold_mul_zero - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55B1F952D1E0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55D445937650)'>
    FAILED test/core/solver/test_solver.py::test_remove_obvious_tautologies - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55D445937650)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55D44C63BB90)'>
    FAILED test/core/solver/test_solver.py::test_subset_of_literal - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55D44C63BB90)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DA6CD8F210)'>
    FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[IsSubset] - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DA6CD8F210)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DA7279CC00)'>
    FAILED test/core/solver/test_solver.py::test_ss_intersect - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DA7279CC00)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DEB29ACAC0)'>
    FAILED test/core/solver/test_solver.py::test_combined_add_and_multiply_with_ranges - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55DEB29ACAC0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55E350221F70)'>
    FAILED test/core/solver/test_solver.py::test_graph_split - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55E350221F70)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55E3DD4DF4F0)'>
    FAILED test/core/solver/test_solver.py::test_fold_ss_transitive - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55E3DD4DF4F0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55FE098E56E0)'>
    FAILED test/core/solver/test_solver.py::test_solve_phase_one - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55FE098E56E0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55FE182D9D60)'>
    FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c1] - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x55FE182D9D60)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x560B57068940)'>
    FAILED test/core/solver/test_solver.py::test_transitive_subset - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x560B57068940)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56211D8581A0)'>
    FAILED test/core/solver/test_solver.py::test_base_unit_switch - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56211D8581A0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56212E4BEAB0)'>
    FAILED test/core/solver/test_solver.py::test_extracted_literal_folding[c0] - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56212E4BEAB0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5625450FA4F0)'>
    FAILED test/core/solver/test_solver.py::test_symmetric_inequality_correlated - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5625450FA4F0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56448AA66FE0)'>
    FAILED test/core/solver/test_solver.py::test_alias_classes - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56448AA66FE0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56449269E230)'>
    FAILED test/core/solver/test_solver.py::test_obvious_contradiction_by_literal - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x56449269E230)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5647C24E8CB0)'>
    FAILED test/core/solver/test_solver.py::test_inequality_to_set - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on <Node[Numbers] '0x5647C24E8CB0)'>

  1 × faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Units.has_unit'> found on Numbers(<uninitialized>)
    FAILED test/core/solver/test_solver.py::test_implication - faebryk.core.node.TraitNotFound: No trait <class 'faebryk.library.Units.has_unit'> found on Numbers(<uninitialized>)

  1 × faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x558361F3DB00.is_assertable)' on <Node[Is] '0x558361F3DB00)'>>
    FAILED test/core/solver/test_solver.py::test_try_fulfill_super_basic[Is] - faebryk.core.solver.solver.NotDeducibleException: Could not deduce predicate: <is_assertable '0x558361F3DB00.is_assertable)' on <Node[Is] '0x558361F3DB00)'>>

```

NOTE TO SELF THURSDAY

- currently going through `test_solver.py`
  - nick fucked me real gud with his clanker code, but should be ok now
- running `./test/runpytesttable.sh -m "not slow" test/core/solver/test_solver.py`
  and then checking test-report.html
- currently trying to fix the ` No trait <class 'faebryk.library.Parameters.is_parameter_operatable'> found on`
  - happens in structural:merge_intersect_subsets, check upstream how that worked
