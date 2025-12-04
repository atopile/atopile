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
