# atopile project

`atopile` is a project building toolchains to bring the best of software development to the world of hardware design.

We're starting with an electronics compiler that takes uses a new language in `.ato` files to describe the hardware design, and compiles it to netlists that can be laid out and fabricated.

These `.ato` files are human readable, and can be version controlled, so you can collaborate with your team on the design of your hardware. They're modular, so you can reuse components from other projects, and share them with the community. They provide a way to save the intelligence of your design and the validation required to make sure it works as intended, so you can be confident that your design will work as expected.

## Development

"gimme everything" `pip install -e ."[test,doc,dev]"`

### Docs

view docs nicely: `mkdocs serve`
