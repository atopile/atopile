from atopile.data.voltage_divider import voltage_divider

from atopile.netlist.graph_to_netlist import generate_netlist_dict_from_graph

v_div = voltage_divider

netlist = generate_netlist_dict_from_graph(v_div)

print(netlist)
