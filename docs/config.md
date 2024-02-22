# Project configuration

## Versioning

Versions within atopile follow the semantic versioning 2.x schema. See https://semver.org for details
Semantic versions may be prefixed with a "v", so `v1.0.0 == 1.0.0`

## `ato.yaml` project config

The `ato.yaml` is significant indicator for a project:

1. It marks the root of a project. The `ato` commands in the CLI is largely dependant upon the `ato.yaml` to know what project you're referring to.
2. It contains project-level configuration information like where to build from, which layouts have what **entry-points**
3. Lists project dependencies and the required versions of those dependencies
4. Specifies what compiler version the project is intended to build with

### Dependencies

Each package listed under the `dependencies:` key is automatically downloaded and installed for users when they run the `ato install`
command from within a project. These dependencies are anticipated to make the project run.

Each dependency may have constraints on its version using the following operators:

Assuming dependency says `my-package <operator>1.2.3` the following table describes whether each of the operators would match.

They're in approximate order of usefulness/recommendation

| Op  | `0.1.1` | `1.1.0` | `1.2.3` | `1.2.4` | `1.3.0` | `1.4.0` | `2.0.0` | Description |
|-----|---------|---------|---------|---------|---------|---------|---------|-------------|
|`^`  |         |         | ✔       | ✔       | ✔       | ✔       |         | >=, up to the next **major** |
|`~`  |         |         | ✔       | ✔       |         |         |         | >=, up to the next **minor** |
|`==` |         |         | ✔       |         |         |         |         | Exactly |
|`*`  | ✔       | ✔       | ✔       | ✔       | ✔       | ✔       | ✔       | Any |
|`!`  | ✔       | ✔       |         | ✔       | ✔       | ✔       | ✔       | Not (usually used in combination with others)|


`>=`, `<=`, `>`, `<` all work, but have niche value. If you need to use them, something's probably broken.


### Compiler version

eg. `ato-version: v0.1.8`

The installed compiler is matched against this value to see if the project is buildable in the current environment.

It's matched using either:
- `~` if the installed compiler version `<1.0.0`
- else `^` (up to the next major)

Practically, this means breaking compiler changes are indicated using the minor (eg. `0.1.0`, `0.2.0`, `0.3.0`, `0.4.0`) until version `1.0.0`.

When you upgrade your compiler with breaking changes, you need to update your project to match the language changes, bumping this version in your project's `ato.yaml` file