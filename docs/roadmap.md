# Roadmap

What the atopile core team are planning to make of this project and approximately how we're planning to get there.

## Near-term Features

Within each category, the features are listed in approximate order of priority.

The top-level features themselves are too, but we'll tackle the basics of some domains before the more advanced features of others.

!!! note "There's a lot to come"
    This is a living document, not making promises, but it's a good place to start if you're interested in what's coming up.
    Additionally, there's a lot (more than not) that's not here yet, either because we haven't articulated it yet, and because this page would be enormous if we did.

### Reuse

#### Language Features

- [x] Inheritance `from`
- [x] Retyping / Replacement `->`
- [x] Physical units `10kOhm` `1uF`
- [x] Tolerances `10kOhm +/- 1%`
- [ ] Composition / [Traits](https://doc.rust-lang.org/book/ch10-02-traits.html)
- [ ] Equations / Expressions; relate the parameters of components to specs and solve at compile time
- [ ] Typing; what is allowed to or must be connected to what?

#### Component Selection

- [x] MVP select jelly-beans from JLCPCB
- [x] Move component database to cloud in order to support more components and component types

#### Quality control

- [x] Generate gerbers in CI
- [ ] DRC in CI
- [ ] Check source code and layouts are in sync

#### Package Management

- [x] MVP -> https://packages.atopile.io/
- [ ] Search function
- [ ] Package details page
- [ ] Package statistics
- [ ] Authentication for uploading packages

#### Dev tools

- [x] VSCode extension
- [ ] VSCode lanaugage server
- [ ] Schematic viewer; imagine side-by-side with the code
- [ ] KiCAD extension

## Non-goals

Things we don't have planned out.

- GUI editor
- No compatibility with `xyz` ECAD tool: it takes away from the core of the project; to fundamentally change how hardware engineers work. Currently integrated tools are largely seen as stepping stones away from the explicit interfaces of the past.
