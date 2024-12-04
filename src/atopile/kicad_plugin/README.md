# KiCAD Plugin

## Development

It's much easier to work on this if you get proper static analysis setup.

To find `pcbnew`:
1. Open the scripting console in pcbnew
2. `import pcbnew`
3. `pcbnew.__file__`
4. Open up your workspace settings: Cmd + Shift + P -> "settings"
5. Remove the file name from the path in step 3
6. Add it like this:
```json
"python.analysis.extraPaths": [
    "<path-copied-from-step-5>"
]
```

KiCAD 8.0 still uses Python 3.9, so all code must be compatible with that.
