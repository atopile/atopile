# TODO move to new fabll

- [x] GraphFunctions -> moved to Node
  - [x] replace GraphFunctions with Node.bind_typegraph
  - [x] change g to tg in GraphFunctions
- [ ] Graph -> GraphView
  - [x] move to fabll
  - [x] replace with TG
  - [ ] get rid of multi graphs (solver)
  - [x] Change Graph import to fabll.Graph
- [ ] Module
  - [ ] isinstance checks
  - [x] rename to fabll.Node
  - [ ] deal with modules vs node
    - [x] get_children_modules
  - [ ] deal with specializations
- [ ] ModuleInterface
  - [ ] isinstance checks
  - [x] rename to fabll.Node
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

##

- node.get_children

## Strategy

## Notes
- rename node.py to fabll.py
- use graph.py as graph 
- use faebrykpy.py as fbrk (consider renaming to fbrk)