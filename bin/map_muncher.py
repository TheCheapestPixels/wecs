"""
Map muncher - Convert property-annotated maps to runnable output.

* If the input file is given as .blend, run blend2bam on it.
* Pretag
* Find all nodes with `linked_collection` tag
  * If such a node also has a `linked_file` tag, the given file is the
    authoritative source for the model to use, and the value of
    `linked_collection` must be the name of the node in that file that
    will be used to attack at this node.
    The file may first have to be converted via blend2bam.
  * If the node does not have a `linked_file` tag, the node and its
    subgraph will be used.
  * Detach and replace with spawn points
  * Post-tag
  * save
"""


def tag_node(graph, pretags):
    for node_name, tags in pretags.items():
        if node_name == '_root':
            node = graph
        else:
            node = graph.find('**/{}'.format(node_name))
        if not node.is_empty():
            for tag_name, tag_value in tags.items():
                node.set_tag(tag_name, tag_value)


def munch_map(graph):
    """
    * Find nodes that have a `linked_collection` tag.
    * If it has a `linked_file` tag
    """

    instances = {}  # 'model source': NodePath

    # Gather instances and replace them with spawn points
    for node in graph.find_all_matches('**/=linked_collection'):
        collection = node.get_tag('linked_collection')

        # Replace node with a spawn point
        spawn_name = 'spawn_point:{}'.format(node.get_name())
        spawn_point = node.attach_new_node(spawn_name)
        spawn_point.wrt_reparent_to(node.get_parent())
        spawn_point.set_tag('collection', collection)
        node.detach_node()

        # If the node's collection is already in the instances,
        # we're done. Otherwise we'll have to extract the node's
        # canonical source from the linked file and save it on
        # its own.
        if collection not in instances:
            instances[collection] = node

            # If a source file is given, rewrite
            # `//<something>.blend` to `<something>.bam`
            if node.has_tag('linked_file'):
                source_file = node.get_tag('linked_file')
                if source_file.endswith('.blend'):
                    source_file = source_file[:-5] + 'bam'
                if source_file.startswith('//'):
                    source_file = source_file[2:]
                node.set_tag('linked_file', source_file)

    return (graph, instances)


if __name__ == '__main__':
    import argparse
    import pathlib
    import yaml
    from direct.showbase.ShowBase import ShowBase

    # Command-line args
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    args = parser.parse_args()
    input_dir = pathlib.Path(args.input_file).parent

    # Load the input file
    ShowBase()
    graph = base.loader.load_model(args.input_file)

    # Pretagging
    with open('pretag.yaml', 'r') as f:
        spec_text = f.read()
        specs = yaml.load(spec_text, Loader=yaml.BaseLoader)
        if specs is not None:
            tag_node(graph, specs)

    # Detach instances, copy or save their model file
    pruned_map, instances = munch_map(graph)

    # Posttagging
    with open('posttag.yaml', 'r') as f:
        spec_text = f.read()
        specs = yaml.load(spec_text, Loader=yaml.BaseLoader)
        if specs is not None:
            for collection, node_specs in specs.items():
                if collection != '_scene':
                    tag_node(instances[collection], node_specs)
                else:
                    tag_node(graph, node_specs)

    for name, node in instances.items():
        print(name)
        for tag_name in node.get_tags():
            print("  {}: {}".format(tag_name, node.get_tag(tag_name)))

    # Save
    # TODO: Invoke blend2bam where needed
    for collection, node in instances.items():
        filename = '{}.bam'.format(collection)
        if not node.has_tag('linked_file'):
            # Use the extracted graph for this collection
            node.write_bam_file(filename)
        else:
            # Extract the node to use from linked files
            linked_file = node.get_tag('linked_file')
            collection_set = base.loader.load_model(
                input_dir / linked_file,
            )
            collection_node = collection_set.find(collection)
            import pdb; pdb.set_trace()
            collection_node.write_bam_file(filename)

    graph.write_bam_file(args.output_file)
