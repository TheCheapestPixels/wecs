"""
How to create munchable files:

* Create your characters, objects, terrain, and put them into a
  collection.
  * Give them a property `instance` with a unique value. It will be used
    as the filename for the de-duplicated instances.
  * Give them a property `entity_type` with a value of `character` or
    `map`. FIXME: There should also be `prop`.
* Assemble your map, save, `blend2bam`
* `python map_muncher.py <input_file>.bam <output_file>.bam` will
  * put nodes tagged `instance` and put them into 
    `<value_of_tag>.bam`
  * replace them with a NodePath named 
    `spawn_point:<name_of_the_original_node>` that has an `instance` tag
    with the same value as the removed node.
* `bin/map_player/main.py <output_file>.bam` will load the file as a
  terrain, scan it for `spawn_point:*` and create an entity according to
  the `instance` and other tags.
"""

import argparse

from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import CollisionSphere

import wecs
from wecs.core import NoSuchUID
from wecs.core import ProxyType
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.panda3d import debug

from wecs.panda3d.constants import FALLING_MASK
from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import CAMERA_MASK


# Break this out into something of its own

from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.character import CharacterController
from wecs.core import System, Component
from wecs.core import Proxy
from wecs.panda3d.camera import Camera
from wecs.panda3d.input import Input
from wecs.panda3d.mouseover import MouseOverable
from wecs.panda3d.mouseover import MouseOverableGeometry
from wecs.panda3d.mouseover import MouseOveringCamera
from wecs.panda3d.mouseover import UserInterface
from wecs.panda3d.mouseover import Pointable
from wecs.panda3d.mouseover import Targetable
from wecs.panda3d.mouseover import Selectable


@Component()
class Embodiable:
    pass


class AvatarUI(System):
    """
    Command rules:
    if not embodied and not targeting_selection:
        selection(goto target)
    if not embodied and targeting_selection:
        selection(idle)
    if embodied and selecting and not targeting_selection:
        selection(goto target)
    if embodied and selecting and targeting_selection:
        selection(idle)
    if embodied and not selecting and targeting_selection:
        self(idle)
    if embodied and not selecting and not targeting_selection:
        self(goto target)
    """
    entity_filters = {
        'cursor': [Input, MouseOveringCamera, UserInterface],
    }
    proxies = {
        'parent': ProxyType(wecs.panda3d.prototype.Model, 'parent'),
    }
    input_context = 'select_entity'
    
    def update(self, entities_by_filter):
        for entity in entities_by_filter['cursor']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                self.process_input(entity, context)

    def process_input(self, entity, context):
        ui = entity[UserInterface]
        mouseover = entity[MouseOveringCamera]

        mouseovered_entity = None
        if mouseover.entity is not None:
            mouseovered_entity = self.world.get_entity(mouseover.entity)
        targeting_self = mouseover.entity == entity._uid

        selected_entity = None
        if ui.selected_entity is not None:
            selected_entity = self.world.get_entity(ui.selected_entity)
        target_entity = None
        if ui.targeted_entity is not None:
            target_entity = self.world.get_entity(ui.targeted_entity)
        point_coordinates = ui.point_coordinates
        targeting_selection = False
        if selected_entity is not None and ui.selected_entity == ui.targeted_entity:
            targeting_selection = True
        
        embodied = Embodiable in entity
        targeting_embodiable = None
        if mouseovered_entity is not None:
            targeting_embodiable = Embodiable in mouseovered_entity
        
        # Now we can evaluate the player's input. First, he clicked to
        # select.
        if context.get('select', False):
            if target_entity is None or Selectable not in target_entity:
                # Selecting while not pointing at a valid target
                # unselects.
                ui.selected_entity = None
                ui.select_indicator.detach_node()
            else:
                # But selecting a selectable entity... selects it.
                if not embodied or mouseover.entity != entity._uid:
                    ui.selected_entity = target_entity._uid
        # The player instead clicked to give a command, and there is a
        # valid target, ...
        elif context.get('command', False):
            # 3rd person mode, giving command with to selected entity
            if not embodied and selected_entity and target_entity and not targeting_selection:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(selected_entity, *action)
            if not embodied and targeting_selection:
                self.command(selected_entity, 'idle')
            if embodied and selected_entity and target_entity and not targeting_selection:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(selected_entity, *action)
            if embodied and ui.selected_entity and target_entity and not targeting_selection:
                self.command(entity, 'idle')
            if embodied and targeting_selection:
                self.command(selected_entity, 'idle')
            if embodied and not ui.selected_entity and targeting_selection:
                self.command(entity, 'idle')
            if embodied and not ui.selected_entity and target_entity and not targeting_self:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(entity, *action)
            if embodied and targeting_self and not ui.selected_entity:
                self.command(entity, 'idle')
        # Now the player clicked to dis-/embody...
        elif context.get('embody', False):
            if not embodied and not targeting_embodiable and selected_entity:
                self.embody(entity, selected_entity)
            if not embodied and targeting_embodiable:
                self.embody(entity, target_entity)
            if embodied and targeting_embodiable and not targeting_self:
                self.jump_body(entity, target_entity)
            if embodied and not targeting_embodiable:
                self.disembody(entity)

    def command(self, entity, *action):
        ai = entity[BehaviorAI]
        ai.behavior = action

    def embody(self, entity, target):
        pc_mind.add(target)
        third_person.add(target)
        self.world.destroy_entity(entity)

    def jump_body(self, entity, target):
        pc_mind.remove(entity)
        third_person.remove(entity)
        pc_mind.add(target)
        third_person.add(target)

    def disembody(self, entity):
        scene = self.proxies['parent'].field(entity)
        pos = entity[Camera].camera.get_pos(scene)
        hpr = entity[Camera].camera.get_hpr(scene)
        pos.z += 0.5
        hpr.y = 0
        hpr.z = 0
        pc_mind.remove(entity)
        if first_person.in_entity(entity):
            first_person.remove(entity)
        if third_person.in_entity(entity):
            third_person.remove(entity)
        spawn_point = {
            wecs.panda3d.prototype.Model: dict(
                parent=scene,
                post_attach=lambda: wecs.panda3d.prototype.transform(
                    pos=pos,
                    hpr=hpr,
                ),
            ),
        }
        observer.add(
            self.world.create_entity(name="Observer"),
            overrides={
                **spawn_point,
            },
        )

            
# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.spawnpoints.Spawn,
    wecs.panda3d.camera.PrepareCameras,
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Interface interactions
    wecs.panda3d.mouseover.MouseOverOnEntity,
    wecs.panda3d.mouseover.UpdateMouseOverUI,
    AvatarUI,
    # Set inputs to the character controller
    wecs.panda3d.ai.Think,
    wecs.panda3d.ai.BehaviorInhibitsDirectCharacterControl,
    wecs.panda3d.character.UpdateCharacter,
    # Character controller
    wecs.panda3d.character.Floating,
    wecs.panda3d.character.Walking,
    wecs.panda3d.character.Inertiing,
    wecs.panda3d.character.Bumping,
    wecs.panda3d.character.Falling,
    wecs.panda3d.character.Jumping,
    wecs.panda3d.character.TurningBackToCamera,
    wecs.panda3d.character.ExecuteMovement,
    # Animation
    wecs.panda3d.animation.AnimateCharacter,
    wecs.panda3d.animation.Animate,
    # Camera
    wecs.panda3d.camera.ReorientObjectCentricCamera,
    wecs.panda3d.camera.CollideCamerasWithTerrain,
    # Debug keys (`escape` to close, etc.)
    wecs.panda3d.debug.DebugTools,
]


game_map = Aspect(
    [
        wecs.panda3d.prototype.Model,
        wecs.panda3d.prototype.Geometry,
        wecs.panda3d.prototype.CollidableGeometry,
        wecs.panda3d.mouseover.MouseOverableGeometry,
        wecs.panda3d.mouseover.Pointable,
        wecs.panda3d.spawnpoints.SpawnMap,
     ],
    overrides={
        wecs.panda3d.prototype.CollidableGeometry: dict(
            mask=FALLING_MASK|BUMPING_MASK|CAMERA_MASK,
        ),
    },
)


# There are characters, which are points in space that can be moved
# around using the `CharacterController`, using either player input or
# AI control.
# They are spawned at one of the map's spawn points.

character = Aspect(
    [
        wecs.mechanics.clock.Clock,
        wecs.panda3d.prototype.Model,
        wecs.panda3d.character.CharacterController,
        wecs.panda3d.spawnpoints.SpawnAt,
    ],
    overrides={
        wecs.mechanics.clock.Clock: dict(
            clock=lambda: factory(wecs.mechanics.clock.panda3d_clock),
        ),
    },
)


# Avatars are characters which have (presumably humanoid) animated
# models that can walk around. Their entities can be found using the
# mouse cursor or other collision sensors.

animated = Aspect(
    [
        wecs.panda3d.prototype.Actor,
        wecs.panda3d.animation.Animation,
    ],
)


walking = Aspect(
    [
        wecs.panda3d.character.WalkingMovement,
        wecs.panda3d.character.InertialMovement,
        wecs.panda3d.character.BumpingMovement,
        wecs.panda3d.character.FallingMovement,
        wecs.panda3d.character.JumpingMovement,
        # wecs.panda3d.character.TurningBackToCameraMovement,
    ],
    #overrides={wecs.panda3d.character.WalkingMovement:dict(turning_speed=400)}
)


avatar = Aspect(
    [
        character,
        animated,
        walking,
        wecs.panda3d.mouseover.MouseOverable,
        wecs.panda3d.mouseover.Targetable,
        Embodiable,
    ],
)


# Disembodied entities are simply characters that can float.
# FIXME: They should probably also fall/bump into things.

disembodied = Aspect(
    [
        character,
        wecs.panda3d.character.FloatingMovement,
    ],
)


# Cameras

first_person = Aspect(
    [
        wecs.panda3d.camera.Camera,
        wecs.panda3d.camera.MountedCameraMode,
    ],
)


third_person = Aspect(
    [
        wecs.panda3d.camera.Camera,
        wecs.panda3d.camera.ObjectCentricCameraMode,
        wecs.panda3d.camera.CollisionZoom,
    ],
)


# Player interface / AI.

pc_mind = Aspect(
    [
        wecs.panda3d.input.Input,
        wecs.panda3d.mouseover.MouseOveringCamera,
        wecs.panda3d.mouseover.UserInterface,
    ],
    overrides={
        wecs.panda3d.input.Input: dict(
            contexts={
                'character_movement',
                'camera_movement',
                'mouse_over',
                'select_entity',
            },
        ),
    },
)


npc_mind = Aspect(
    [
        wecs.panda3d.ai.BehaviorAI,
        wecs.panda3d.mouseover.Selectable,
    ],
)


# States of being

observer = Aspect(
    [
        disembodied,
        first_person,
        pc_mind,
    ],
)


player_character = Aspect(
    [
        avatar,
        third_person,
        pc_mind,
        npc_mind,
    ],
)


non_player_character = Aspect(
    [
        avatar,
        npc_mind,
    ],
)


# Load the map

parser = argparse.ArgumentParser()
parser.add_argument('map_file')
args = parser.parse_args()


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

# Scan map for spawn points and instantiate

def create_character(model, spawn_point, aspect):
    # FIXME: There are a lot of constants here that should be drawn
    # from the model itself and the spawn point node.
    bumper_node = model.find('**/=bumper')
    bumper_spec = {
        'bumper': dict(
            shape=CollisionSphere,
            center=bumper_node.get_pos(),
            radius=bumper_node.get_scale().x,
        ),
    }
    lifter_node = model.find('**/=lifter')
    lifter_spec = {
        'lifter': dict(
            shape=CollisionSphere,
            center=lifter_node.get_pos(),
            radius=lifter_node.get_scale().x,
        ),
    }
    mouseover_node = model.find('**/=mouseover')
    pos = mouseover_node.get_pos()
    scale = mouseover_node.get_scale().x
    mouseover_spec = CollisionSphere(pos.x, pos.y, pos.z, scale)

    aspect.add(
        base.ecs_world.create_entity(name="Playerbecca"),
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
