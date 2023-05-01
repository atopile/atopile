#%%
import yaml
from atopile.model.model import Graph, VertexType
from contextlib import contextmanager

class GraphBuilderFromYaml:
    def __init__(self):
        self.source_file = None
        self.graph = Graph()
        self._parsed_files = []
        self._context_stack = []

    def get_context(self):
        # eg. some_file.ato/some_block
        if self._context_stack:
            return self._context_stack[-1]
        return None

    @contextmanager
    def context(self, context):
        self._context_stack.append(context)
        yield
        self._context_stack.pop()

    @contextmanager
    def subcontext(self, context):
        if self.get_context() is None:
            new_context = context
        else:
            new_context = self.get_context() + "/" + context

        with self.context(new_context):
            yield

    def find_vertex_by_code_ref(self, ref: str) -> str:
        pass

    def build_block(self, data: dict):
        if "from" in data and data["from"] is not None:
            assert self.graph.get_vertex_type(data["from"]) == VertexType.block, f"Cannot instantiate from non-block: {data['from']}"
            self.graph.create_instance(data["from"], data["name"], defined_by=self.get_context())
        else:
            self.graph.add_vertex(data["name"], VertexType.block, defined_by=self.get_context())

        with self.subcontext(data["name"]):
            self.build_statements(data["inner"])

    def build_signal(self, data: dict):
        self.graph.add_vertex(data["name"], VertexType.ethereal_pin, part_of=self.get_context())

    def build_package(self, data: dict):
        if "from" in data and data["from"] is not None:
            assert self.graph.get_vertex_type(data["from"]) == VertexType.package, f"Cannot instantiate from non-package: {data['from']}"
            self.graph.create_instance(data["from"], data["name"], defined_by=self.get_context())
        else:
            self.graph.add_vertex(data["name"], VertexType.package, defined_by=self.get_context())

        with self.subcontext(data["name"]):
            for pin in data["pins"]:
                self.graph.add_vertex(pin, VertexType.pin, part_of=self.get_context())

    def build_connection(self, data: dict):
        pass

    def build_statements(self, statements: list):
        for data in statements:
            if data["type"] == "import":
                self.build_from_file(data)
            elif data["type"] == "block":
                self.build_block(data)
            elif data["type"] == "signal":
                self.build_signal(data)
                print(f"instantiate {data['name']}")
            elif data["type"] == "package":
                self.build_package(data)
                print(f"pin {data['name']}")
            elif data["type"] == "connect":
                self.build_connection(data)
            else:
                raise Exception(f"Unknown statement type: {data['type']}")

    def build_from_string(self, data: dict, context: str = "__string_input__"):
        with self.context(context):
            data = yaml.safe_load(data)
            self.graph.add_vertex(self.get_context(), VertexType.block)
            self.build_statements(data)

    def build_from_file(self, path: str):
        if path in self._parsed_files:
            return

        if path in self._context_stack:
            raise Exception(f"Circular dependency detected: {path}")

        with self.context(path):
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                self.graph.add_vertex(self.get_context(), VertexType.block)
                self.build_statements(data)
        self._parsed_files.append(path)

#%%
test = """
-
    type: block
    name: test_block
    inner:
    -
        type: signal
        name: test_signal
    -
        type: signal
        name: test_signal2
    -
        type: signal
        name: test_signal2
    -
        type: connect
        from: test_signal
        to: test_signal2
"""

parser = GraphBuilderFromYaml()
parser.build_from_string(test)
parser.graph.plot(debug=True)

# %%
