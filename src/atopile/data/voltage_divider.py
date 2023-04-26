# %%
from atopile import model
import igraph as ig
from atopile.data.resistor import resistor

voltage_divider = ig.Graph(directed=True)

voltage_divider = model.add_block(voltage_divider, resistor, 'res1')
voltage_divider = model.add_block(voltage_divider, resistor, 'res2')
voltage_divider = model.add_block(voltage_divider, resistor, 'res3')
voltage_divider = model.add_block(voltage_divider, resistor, 'res4')