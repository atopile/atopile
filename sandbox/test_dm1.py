#%%
from atopile.model2.builder1 import Dizzy, build
from atopile.dev.parse import parse_as_file
from atopile.dev.dm1_vis import Wendy
from pathlib import Path
from atopile.model2.parse import parse_file

dizzy = Dizzy("test.ato")
wendy = Wendy()

# %%

# Create a Path object for the directory
servo_path = Path("/Users/narayanpowderly/Documents/atopile-workspace/servo-drive/elec/src")

# Call the glob() method with the pattern "**/*.ato"
ato_files = servo_path.glob("**/*.ato")

# Iterate over the returned generator and process each file
# for ato_file in ato_files:
#     # Print the file path
#     print(ato_file)

#     # Read the file contents
#     file_contents = ato_file.read_text()

#     # Print the file contents
#     # print(file_contents)

#     # Process the file contents with your Dizzy and Wendy instances
# get the first file
ato_file = next(ato_files)
print(ato_file)
# tree = dizzy.visitFile_input(parse_as_file(file_contents))
tree = parse_file(ato_file)
dizzy_map = build({ato_file: tree}, None)

wendy.print_tree(dizzy_map[ato_file])
# %%

# Create a Path object for the file
ato_file = Path("/Users/narayanpowderly/Documents/atopile-workspace/servo-drive/elec/src/buck_reg.ato")

# Print the file path
print(ato_file)

# Read the file contents
file_contents = ato_file.read_text()

# Print the file contents
print(file_contents)

# Process the file contents with your Dizzy and Wendy instances
tree = dizzy.visitFile_input(parse_as_file(file_contents))
wendy.print_tree(tree)
# %%
