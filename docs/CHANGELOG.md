# Change Log

## v0.3.x

Firstly, thanks for using atopile! It's been a ride, and we're glad you're here. 🙌

### Changed Commands

Add `--help` after any command to see new options in the CLI. This is always the most accurate source of information.

| Old | New |
|-----|-----|
| `ato install --jlcpcb` | `ato create component` |


### I'm seeing a bunch of `DeprecationWarning`

There will be a LOT of new deprecation warnings you'll see.

For the most part, it's safe to ignore them for the minute, and we plan to make the breaking changes in 0.4.0

Upgrading will give you more access to features as they're added, but there's no need to rush if you're content.

### PCBs are now directly modified

This means no more need to open the PCB file, import the netlist and cycle.

`ato build` now directly modifies the PCB file as required on each build.


### Standard Library (previously `generics`) is now shipped built-in!

This vastly improves our ability to version and iterate on the standard library, use the best practices and latest features.

See [`library`](https://github.com/atopile/atopile/tree/main/src/faebryk/library) for the latest and greatest.

It should be better documented. If this is important for you, please vote on the issue: #936
