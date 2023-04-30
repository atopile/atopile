# %%
from ..src.atopile.model.model import Graph, VertexType, EdgeType

g = Graph()
g.add_vertex("resistor.ato", VertexType.block)
g.add_vertex("seed", VertexType.block, defined_by="resistor.ato")
# g.add_vertex("block", VertexType.block, defined_by="resistor.ato/seed")
g.add_vertex("package", VertexType.package, defined_by="resistor.ato/seed")
g.add_vertex("ethereal_pin", VertexType.ethereal_pin, defined_by="resistor.ato/seed")
g.add_vertex("pin", VertexType.pin, defined_by="resistor.ato/seed/package")

g.create_instance("resistor.ato/seed", "resistor", defined_by="resistor.ato")
g.create_instance("resistor.ato/resistor/package", "resistor_package", part_of="resistor.ato/resistor")
g.create_instance("resistor.ato/resistor/ethereal_pin", "1", part_of="resistor.ato/resistor")
g.create_instance("resistor.ato/resistor/ethereal_pin", "2", part_of="resistor.ato/resistor")
g.create_instance("resistor.ato/resistor/resistor_package/pin", "1", part_of="resistor.ato/resistor/resistor_package")
g.create_instance("resistor.ato/resistor/resistor_package/pin", "2", part_of="resistor.ato/resistor/resistor_package")

g.create_instance("resistor.ato/seed", "vdiv", defined_by="resistor.ato")
g.create_instance("resistor.ato/resistor", "vdiv_res_1", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/resistor", "vdiv_res_2", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "INPUT", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "OUTPUT", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "GROUND", part_of="resistor.ato/vdiv")

g.add_connection("resistor.ato/vdiv/INPUT", "resistor.ato/vdiv/vdiv_res_1/resistor_package/1")
g.add_connection("resistor.ato/vdiv/OUTPUT", "resistor.ato/vdiv/vdiv_res_1/resistor_package/2")
g.add_connection("resistor.ato/vdiv/GROUND", "resistor.ato/vdiv/vdiv_res_2/resistor_package/2")
g.add_connection("resistor.ato/vdiv/vdiv_res_1/resistor_package/2", "resistor.ato/vdiv/vdiv_res_2/resistor_package/1")

g.create_instance("resistor.ato/vdiv", "a_voltage_divider", part_of="resistor.ato")

g.plot(debug=True)
# %%
