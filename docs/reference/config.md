# `ato.yaml` Config Reference

### [`ato-version`](#ato-version) {: #ato-version }

!json-schema::$defs.ProjectConfig.properties.ato-version.description

**Default value**: current compiler version

**Type**: `str`

**Example usage**:

```toml title="ato.yaml"
ato-version: 0.3.0
```

### [`paths.src`](#paths.src) {: #paths.src }

!json-schema::$defs.ProjectPaths.properties.src.description

**Default value**: `elec/src`

**Type**: `str`

**Example usage**:

```toml title="ato.yaml"
paths:
  src: "./"
```

### [`paths.layout`](#paths.layout) {: #paths.layout }

!json-schema::$defs.ProjectPaths.properties.layout.description

**Default value**: `elec/layout`

**Type**: `str`

**Example usage**:

```toml title="ato.yaml"
paths:
  layout: "./"
```

### [`dependencies`](#dependencies) {: #dependencies }

!json-schema::$defs.Dependency.description

**Default value**: `[]` or no dependencies

**Type**:

| Field | Type | Description | Default |
| ----- | ---- | ----------- | ------- |
| `name` | `str` | The name of the dependency | No default and required |
| `version_spec` | `str` | The version specifier for the dependency | Latest tagged version or commit on `main` |
| `link_broken` | `bool` | Whether the link to the upstream version is maintained / broken | `false` |
| `path` | `str` | The path to the dependency within this project | `.ato/modules/<name>` |

**Example usage**:

```toml title="ato.yaml"
dependencies:
  - name: rp2040
    version_spec: ">=3.0.0,<4.0.0"
```

### [`builds`](#builds) {: #builds }

!json-schema::$defs.BuildTargetConfig.description

**Default value**: `{}` or no build targets

**Type**: `dict` (see "builds.name" etc... below for details)


### [`builds.entry`](#builds.entry) {: #builds.entry }

!json-schema::$defs.BuildTargetConfig.properties.entry.description

**Default value**: Required, no default

**Type**: `str`

**Example usage**:

```toml title="ato.yaml"
builds:
    default:
        entry: some_file.ato:App
```
