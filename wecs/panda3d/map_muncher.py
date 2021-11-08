def load_map():
    map_node = base.loader.load_model(args.map_file)
    
    if not map_node.find('**/+GeomNode').is_empty():
        # There's geometry in the map; It's actually a map!
        game_map.add(
            base.ecs_world.create_entity(name="Map"),
            overrides={
                wecs.panda3d.prototype.Geometry: dict(node=map_node),
            }
        )
    else:
        base.ecs_world.create_entity(
            wecs.panda3d.spawnpoints.SpawnMap(),
            wecs.panda3d.prototype.Model(node=map_node),
            name="Map",
        )


def create_character(model, spawn_point, aspect, name='Character'):
    # FIXME: There are a lot of constants here that should be drawn
    # from the model itself and the spawn point node.
    bumper_node = model.find('**/=bumper')
    bumper_spec = {
        'bumper': dict(
            shape=CollisionSphere,
            center=bumper_node.get_pos(),
            radius=bumper_node.get_scale().x * 2,
        ),
    }
    lifter_node = model.find('**/=lifter')
    lifter_spec = {
        'lifter': dict(
            shape=CollisionSphere,
            center=lifter_node.get_pos(),
            radius=lifter_node.get_scale().x * 2,
        ),
    }
    mouseover_node = model.find('**/=mouseover')
    pos = mouseover_node.get_pos()
    scale = mouseover_node.get_scale().x
    mouseover_spec = CollisionSphere(pos.x, pos.y, pos.z, scale)

    aspect.add(
        base.ecs_world.create_entity(name=name),
        overrides={
            wecs.panda3d.prototype.Geometry: dict(
                file=model_file,
            ),
            wecs.panda3d.prototype.Actor: dict(
                file=model_file,
            ),
            wecs.panda3d.character.BumpingMovement: dict(
                solids=bumper_spec,
            ),
            wecs.panda3d.character.FallingMovement: dict(
                solids=lifter_spec,
            ),
            MouseOverable: dict(
                solid=mouseover_spec,
            ),
            wecs.panda3d.spawnpoints.SpawnAt: dict(
                name=spawn_point,
            ),
        },
    )


def create_map(model):
    game_map.add(
        base.ecs_world.create_entity(name="Map"),
        overrides={
            wecs.panda3d.prototype.Geometry: dict(node=model),
        },
    )


for node in map_node.find_all_matches('**/spawn_point:*'):
    # This is Python 3.9+:
    # spawn_name = node.get_name().removeprefix('spawn_point:')
    spawn_point = node.get_name()
    spawn_name = spawn_point[len('spawn_point:'):]
    collection = node.get_tag('collection')
    model_file = '{}.bam'.format(collection)
    model = base.loader.load_model(model_file)
    entity_type = model.get_tag('entity_type')

    print("Creating {} from {} at {}".format(entity_type, collection, spawn_name))
    if entity_type == 'character':
        character_type = node.get_tag('character_type')
        if character_type == 'player_character':
            create_character(model, spawn_point, player_character)
        elif character_type == 'non_player_character':
            create_character(model, spawn_point, non_player_character)
    elif entity_type == 'map':
        create_map(model)
    elif entity_type == 'nothing':
        pass
    else:
        print("Unknown entity type '{}'.".format(entity_type))
