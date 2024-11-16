# Imports

You can import assets by specifying what you want to import and where you want to import it from using the following syntax within your `.ato` files:

`from "where.ato" import What, Why, Wow`

Notes on that statement:
- add quotes on the "where.ato" - it's a string
- `What`, `Why` and `Wow` are capitalised because they are in the source file. It has to match precisely - it's a type and types should be capitalised, though this isn't enforced and you can import things other than types from other files

The import statements are with respect to the current project (the root of which is where your `ato.yaml` is placed), or within the standard library (`.ato/modules/`)

!!! warning
    You'll likely see import statements in the form of `import XYZ from "abc.ato"`. This is a legacy syntax and will be removed in the future. Please use the new syntax.

    It also doesn't support importing multiple things on the same line.
