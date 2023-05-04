#%%
# %load_ext autoreload
# %autoreload 2
from atopile.model.model2 import Model, VertexType, EdgeType

#%%
m = Model()
file_path = m.new_vertex(VertexType.file, "toy.ato")

# define a resistor component - IRL would likely come from a library
resistor_path = m.new_vertex(VertexType.component, "Resistor", part_of=file_path)
m.new_vertex(VertexType.pin, "1", part_of=resistor_path)
m.new_vertex(VertexType.pin, "2", part_of=resistor_path)

# define a voltage divider module, containing two resistors
vdiv_path = m.new_vertex(VertexType.module, "Vdiv", part_of=file_path)
vdiv_a = m.new_vertex(VertexType.signal, "a", part_of=vdiv_path)
vdiv_center = m.new_vertex(VertexType.signal, "center", part_of=vdiv_path)
vdiv_b = m.new_vertex(VertexType.signal, "b", part_of=vdiv_path)

# NOTE: these should be created as instances of the resistor component
r1_path = m.new_vertex(VertexType.component, "R1", part_of=vdiv_path)
m.new_edge(EdgeType.instance_of, r1_path, resistor_path)
r1_1_path = m.new_vertex(VertexType.pin, "1", part_of=r1_path)
r1_2_path = m.new_vertex(VertexType.pin, "2", part_of=r1_path)

r2_path = m.new_vertex(VertexType.component, "R2", part_of=vdiv_path)
m.new_edge(EdgeType.instance_of, r2_path, resistor_path)
r2_1_path = m.new_vertex(VertexType.pin, "1", part_of=r2_path)
r2_2_path = m.new_vertex(VertexType.pin, "2", part_of=r2_path)

# connect the resistors to the module signals
m.new_edge(EdgeType.connects_to, vdiv_a, r1_1_path)
m.new_edge(EdgeType.connects_to, vdiv_center, r1_2_path)
m.new_edge(EdgeType.connects_to, r1_2_path, r2_1_path)
m.new_edge(EdgeType.connects_to, r2_2_path, vdiv_b)


# %%
m.plot(debug=True)

# %%
