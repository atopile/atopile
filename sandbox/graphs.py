#%%
import igraph as ig
import uuid

g1 = ig.Graph(n=3, edges=[(1,2)])
g2 = ig.Graph(n=3, edges=[(0,1)])
g1.vs[:]['name'] = ['a', 'b', 'c']
g2.vs[:]['name'] = ['d', 'e', 'f']
print(g1)
print(g2)

# %%
g2.connected_components(mode='weak')[0]
# %%
# figure out subgraphs
sg = g2.subgraph(g2.vs.select(name_in=['d', 'e']))
print(sg)
# %%
g3 = g1 + sg
# %%
print(g3)
# %%
print(g1)
# %%
print(g2)
# %%
g1.vs.select(name_eq='a')['test2'] = 'test2'
# %%
print(g1)
# %%
g = ig.Graph(
    n=5,
    edges=[(0,1), (1,2), (1, 3)],
    directed=True,
    vertex_attrs=
        {'name': ['a', 'b', 'c', 'd', 'e'],
         'type': ['a', 'a', 'b', 'b', 'b']},
    edge_attrs=
        {'type': ['a', 'a', 'b']}
)

ig.plot(g.subgraph_edges(g.es.select(type_eq='b'), delete_vertices=False))

# %%
