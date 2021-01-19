def post_tag_map(graph, pretags):
    for node_name, tags in pretags.items():
        node = graph.find(node_name)
        for tag_name, tag_value in tags.items():
            node.set_tag(tag_name, tag_value)


def munch_map(graph):
    instances = {}

    # Gather instances and replace them with spawn points
    for node in graph.find_all_matches('**/=instance'):
        instance_type = node.get_tag('instance')
        instances[instance_type] = node

        # Add spawn point
        spawn_name = 'spawn_point:{}'.format(node.get_name())
        spawn_point = node.attach_new_node(spawn_name)
        spawn_point.wrt_reparent_to(node.get_parent())
        spawn_point.set_tag('instance', instance_type)

        # Remove instance from scene graph
        node.detach_node()

    return (graph, instances)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    args = parser.parse_args()

    from direct.showbase.ShowBase import ShowBase
    ShowBase()
    graph = base.loader.load_model(args.input_file)

    import yaml
    with open('pretag.yaml', 'r') as f:
        spec_text = f.read()
        specs = yaml.load(spec_text, Loader=yaml.BaseLoader)
        post_tag_map(graph, specs)

    pruned_map, instances = munch_map(graph)
    
    # Save
    graph.write_bam_file(args.output_file)
    for instance_type, subgraph in instances.items():
        filename = '{}.bam'.format(instance_type)
        subgraph.write_bam_file(filename)
