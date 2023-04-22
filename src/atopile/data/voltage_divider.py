# %%
from atopile import model
import igraph as ig
from atopile.data.resistor import resistor

voltage_divider = ig.Graph(directed=True)

voltage_divider += resistor
voltage_divider += resistor
voltage_divider += resistor
voltage_divider += resistor

# %%

voltage_divider.add_edges([(1, 7), (13, 19)], {'type': ['connects_to'] * 2})

#model.plot(voltage_divider)
# %%
