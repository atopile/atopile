#!/bin/bash

VERSION=1000.0.0
RELPATH=..
# TODO: Currently a bug in cursor so uninstall & install don't work afaik
# instead just right click on the extension and click install vsix
# then wait for the popup (installed extension)
# then run > Developer: Restart Extension Host
AUTO=0

pushd $(dirname $0)/$RELPATH

# Package the extension
vsce package --pre-release --no-git-tag-version --no-update-package-json $VERSION || exit 1

if [ $AUTO -eq 1 ]; then
    # TODO might not be needed
    # Uninstall the extension
    cursor --profile default --uninstall-extension atopile.atopile || exit 1
    # Install the extension
    cursor --profile default --install-extension atopile-$VERSION.vsix || exit 1
fi

popd