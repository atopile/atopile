"""
TODO: stick this in a useful function or class of some kind
"""


components = list(filter(match_components, all_descendants(ROOT)))
bom = defaultdict(dict)
#JLC format: Comment(whatever might be helpful)	Designator	Footprint	LCSC
for component in components:
    try:
        mpn = get_mpn(component)
    except KeyError:
        continue
    # add to bom keyed on mpn
    bom[mpn]["value"] = get_value(component)
    bom[mpn]["footprint"] = get_footprint(component)
    bom[mpn]["designator"] = get_designator(component)

import csv

from rich import print
from rich.table import Table

# Create a table
table = Table(show_header=True, header_style="bold magenta")
table.add_column("Comment")
table.add_column("Designator")
table.add_column("Footprint")
table.add_column("LCSC")

# Add rows to the table
for mpn, data in bom.items():
    table.add_row(str(data['value']), data['designator'], data['footprint'], mpn)

# Print the table
print(table)

# generate csv
# with open('bom.csv', 'w', newline='') as csvfile:
#     fieldnames = ['Comment', 'Designator', 'Footprint', 'LCSC']
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

#     writer.writeheader()
#     for mpn, data in bom.items():
#         writer.writerow({'Comment': data['value'], 'Designator': data['designator'], 'Footprint': data['footprint'], 'LCSC': mpn})
