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

## Linked vs. Vendored

By default, packages are linked to your project. This means that the dependency is installed

You can also vendor a package. This will copy the package into your project's `vendor` directory.

Use `--vendor` to vendor a package. This will copy the package into your project's `vendor` directory.

```bash
ato install --vendor esp32-s3
```
