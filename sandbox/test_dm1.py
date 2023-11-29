#%%
from atopile.model2.datamodel1 import Dizzy
from atopile.dev.parse import parse_as_file
from atopile.dev.dm1_vis import Wendy
from pathlib import Path
from atopile.model2.parse import parse

dizzy = Dizzy("test.ato")
wendy = Wendy()

# %%

# Create a Path object for the directory
servo_path = Path("../../servo-drive/elec/src")

# Call the glob() method with the pattern "**/*.ato"
ato_files = servo_path.glob("**/*.ato")

# Iterate over the returned generator and process each file
for ato_file in ato_files:
    # Print the file path
    print(ato_file)

    # Read the file contents
    file_contents = ato_file.read_text()

    # Print the file contents
    # print(file_contents)

    # Process the file contents with your Dizzy and Wendy instances
    tree = dizzy.visitFile_input(parse_as_file(file_contents))
    wendy.print_tree(tree)
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
