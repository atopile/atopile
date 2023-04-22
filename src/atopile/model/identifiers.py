import uuid
import hashlib
import igraph as ig
from .find import ancestory_dot_com

def generate_uid_from_path(path: str) -> str:
    path_as_bytes = path.encode('utf-8')
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return uuid.UUID(bytes=hashed_path)

def get_vertex_path(g: ig.Graph, vid: int):
    return ".".join(g.vs[ancestory_dot_com(g, vid)[::-1]]['ref'])
