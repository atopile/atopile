---
name: extension-dev
description: "Use when modifying the VS Code extension or webviews in this repo."
---

VS Code webviews run in sandboxed iframes, so do not use `window.alert`, `window.confirm`, or `window.prompt`; use a webview-native dialog such as `<dialog>` or an extension-host modal instead.
