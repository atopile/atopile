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
- [ ] re-enable has_usage_example MakeChild and has_simple_value_representation
- [ ] consider making negative=True default (default domain creates no constraints, then we can remove DOMAIN_SKIP)

NOTE TO SELF WEDNESDAY

- currently going through `test_solver.py`
- running `./test/runpytesttable.sh -m "not slow" test/core/solver/test_solver.py`
  and then checking test-report.html
- got rid of all superficial errors

  - now only slow / contradiction / assert result errors (actual solver errors) left

    - slowly start going one-by-one through solver errors
      (might want to first focus on the lit folding to make sure)

NOTE TO SELF FRIDAY

- trying to get rid of the memory leaks in the tests

  - its not the most important thing ever, but having a good understanding here is key for the tool
  - last thing is auto destroy solver state to clean intermediate graphs
  - for some reason we got a bunch of crashes
  - also asked clanker to expose total memory allocated in html

- [x] fix hypothesis ci (parametrize)
- [x] errors in test report
- [ ] measure mem usage of single node, edge, etc
