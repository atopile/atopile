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

======= 106 failed, 462 passed, 5 skipped, 35 xfailed, 1 xpassed, 137 errors in 23.45s ========
