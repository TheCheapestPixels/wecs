from graphviz import Graph


# Example of use:
#
# from wecs.graphviz import system_component_dependency
# system_component_dependency(
#     world,
#     omit_systems=[
#         systems.PrintOutput,
#         systems.ReadInput,
#     ],
# )


def system_component_dependency(world, filename="dependency",
                                omit_systems=None):
    if omit_systems is None:
        omit_systems = []
    dependency_graph = world.get_system_component_dependencies()
    systems = [s for s in dependency_graph.keys()
               if type(s) not in omit_systems]
    components = set()
    for s in dependency_graph.values():
        components.update(s)

    dot = Graph(
        comment="System Component Dependencies",
        filename=filename,
        graph_attr=dict(
            rankdir='LR',
        ),
        node_attr=dict(
            group='A',
        ),
    )

    for system in systems:
        dot.node(repr(system))
    for component in components:
        dot.node(repr(component))
    for system in systems:
        for dependency in dependency_graph[system]:
            dot.edge(repr(system), repr(dependency))

    dot.render(format='png')
