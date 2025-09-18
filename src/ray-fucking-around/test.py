import time
from faebryk.core.parameter import Parameter, p_field, Domain, Boolean
# from faebryk.core.cpp import *
from faebryk.core.node import Node
from faebryk.core.solver.defaultsolver import DefaultSolver

class TopLevelProject(Node):
    required_atopile_version: Parameter
    is_project = p_field(domain=Boolean())

    def __postinit__(self):

        start_time_1 = time.perf_counter()

        self.is_project.alias_is(True)
        self.get_child_by_name('is-project').Literal = 1

        end_time_1 = time.perf_counter()
        print(f"Section 1 time: {(end_time_1 - start_time_1) * 1000:.4f} ms")

        start_time_2 = time.perf_counter()

        is_package = Parameter()
        is_package.Literal = 1
        self.add(is_package, name="is-package")

        end_time_2 = time.perf_counter()
        print(f"Section 2 time: {(end_time_2 - start_time_2) * 1000:.4f} ms")

        start_time_3 = time.perf_counter()

        self.add(Parameter(), name="some-parameter")
        some_parameter = self.get_child_by_name('some-parameter')
        some_parameter.Literal = 1
        
        end_time_3 = time.perf_counter()
        print(f"Section 3 time: {(end_time_3 - start_time_3) * 1000:.4f} ms")


class MyNode(Node):
    param1: Parameter
    param2: Parameter
    param3 = p_field(domain=Boolean())
    def __postinit__(self):
        # Is(param1, 10)
        self.param1.alias_is(10)


        # Is(Multiply(param1, 5), param2)
        self.param2.alias_is(self.param1 * 5)

# children = project_instance.children.get_children()
# print(children)

# print(project_instance.get_child_by_name('is-package').Literal)
# print(project_instance.get_child_by_name('is-project').Literal)
# print(project_instance.get_child_by_name('some-parameter').Literal)

solver = DefaultSolver()
node = MyNode()
solver.simplify_symbolically(node.get_graph())
print(node.param1.get_literal())
print(solver.inspect_get_known_supersets(node.param2))
# rint(node._my_param2.get_literal())