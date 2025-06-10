#!/bin/bash

VERSION=1000.0.0
RELPATH=..

pushd $(dirname $0)/$RELPATH

# Package the extension
vsce package --pre-release --no-git-tag-version --no-update-package-json $VERSION || exit 1

# Uninstall the extension
cursor --profile default --uninstall-extension atopile.atopile || exit 1
# Install the extension
cursor --profile default --install-extension atopile-$VERSION.vsix || exit 1

popd