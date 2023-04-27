# %%
from atopile import model

from atopile.data.voltage_divider import voltage_divider

from atopile.netlist.graph_to_netlist import generate_nets_dict_from_graph
from atopile.netlist.graph_to_netlist import generate_component_list_from_graph

v_div = voltage_divider

#nets = generate_nets_dict_from_graph(v_div)

#print(nets)

print(generate_component_list_from_graph(v_div))

# %%
