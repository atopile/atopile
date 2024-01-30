# Imports

You can import assets by specifying what you want to import and where you want to import it from using the following syntax within your `.ato` files:

`import What from "where.ato"`

Notes on that statement:
- add quotes on the "where.ato" - it's a string
- `What` is capitalised - it's a type and types should be capitalised, though this isn't enforced and you can import things other than types from other files

The import statements are with respect to the current project, or within the standard library (`.ato/modules/`)