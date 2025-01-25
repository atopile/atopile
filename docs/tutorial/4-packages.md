# 4. Packages

One of the huge benefits to designing circuit boards with code is that it unlocks modularity. As in software, this modularity means you can package up and reuse modules other's have developed and tested.

## Finding packages

Check [first-party packages](https://packages.atopile.io/) for a list of designed and used internally at atopile. Discussion planning to open this up publicaly: see ?495
These have all been built, are known to work and come with a functioning layout too.

Alternatively, Google is your friend! Packages are often publicly available on github or other repositories.

## Installing packages

Use `ato install` to install packages.

For example, this command will install the package named `esp32-s3` from atopile's internal package repository.

```bash
ato install esp32-s3
```

You can also directly specify a git repo URL to install from:

```bash
ato install https://github.com/atopile/rp2040
```

This will install the `rp2040` package from the given repo.

## Versioning

`ato` uses version numbers in the format `x.y.z`, and we recommend using [semantic versioning](https://semver.org/).

Properly-specified dependency versions mean that you will get upgrades automatically. That said, if you're too loose with your version requirements, you may end up with a lot of upgrades that break things.

By default, `ato install` is very tight with version requirements, and, without other directives, will add a specific githash as your dependency's version requirement. This means you will always get that exact version of the package when installed on new computers or in CI, but that's often too tight.

`ato` also supports the following version operators:

| Operator | Description |
| -------- | ----------- |
| `*`      | Any version |
| `^`      | Any version with the same major version |
| `~`      | Any version with the same major and minor version |
| `!`      | Not this version |
| `==`     | Exactly this version |
| `>=`     | Any version greater than or equal to |
| `<`      | Any version less than |

Version requirements are "AND"ed together when separated by a comma, and can be "OR"ed together when separated by a `||`.

Versions may, but don't need to have a `v` prefix.

That means, if you want version `1.2.3` or anything within `1.3`, you can specify `1.2.3 || ~1.3.0`.

The most common operator is `^`, which means "any version with the same major version", which when coupled with semantic versioning means "any version that does at least as much as the version you're specifying without breaking things".

That means you might often use a command like `ato install "some_package^1.2.3"` to add that package to your project.

Versions are pulled from `git` tags.

You can use version requirements to specify which version of a package should be installed.

Additionally, `git` refs are supported when prefixed with an `@`. For example `ato install some-package@main` will always get the `main` branch of the `some-package` package. Very unstable!

## Linked vs. Vendored

By default, packages are installed in the directory `.ato/modules`, which isn't version controlled. Other people installing your project will need to run `ato install` to install the same packages on their computer. This is how packages typically work in software, and usually works well (as long as you're using good versioning), however, if you plan on making changes to a package that don't make sense to commit back to the upstream repo, you may want to vendor the package instead.

```bash
ato install --vendor esp32-s3
```

This will copy the package into your project's `src` directory instead, and break the link to the upstream repo.


## Sharing packages you've built

To the package manager: coming soon! :rocket: ?495

For now, publish a public repo with a README.md that describes the package and how to use it.
We'd love you to share on discord too!
