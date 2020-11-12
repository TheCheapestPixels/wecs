from dataclasses import field

from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import CollisionSphere

# from wecs import cefconsole
import wecs
from wecs.core import NoSuchUID
from wecs.core import ProxyType
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.panda3d import debug

from wecs.panda3d.constants import FALLING_MASK
from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import CAMERA_MASK


# Behavior and interface stuff
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionRay
from panda3d.core import CollisionNode
from panda3d.core import NodePath

from wecs.core import System, Component
from wecs.core import Proxy
from wecs.panda3d.camera import Camera
from wecs.panda3d.input import Input
from wecs.panda3d import prototype

from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.character import CharacterController


MOUSEOVER_MASK = 1 << 4


@Component()
class MouseOverable:
    solid: object
    mask = MOUSEOVER_MASK
    _node: None = None


@Component()
class MouseOverableGeometry:
    mask = MOUSEOVER_MASK


@Component()
class MouseOveringCamera:
    entity: object = None
    collision_entry: object = None

    
class MouseOverOnEntity(System):
    entity_filters = {
        'mouseoverable': [Proxy('model'), MouseOverable],
        'mouseoverable_geometry': [Proxy('geometry'), MouseOverableGeometry],
        'camera': [Camera, Input, MouseOveringCamera],
    }
    proxies = {
        'model': ProxyType(prototype.Model, 'node'),
        'geometry': ProxyType(prototype.Geometry, 'node'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.traverser = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        
        self.picker_ray = CollisionRay()
        self.picker_node = CollisionNode('mouse ray')
        self.picker_node.add_solid(self.picker_ray)
        self.picker_node.set_from_collide_mask(MOUSEOVER_MASK)
        self.picker_node.set_into_collide_mask(0x0)
        self.picker_node_path = NodePath(self.picker_node)

        self.traverser.add_collider(self.picker_node_path, self.queue)

    def enter_filter_mouseoverable(self, entity):
        model_proxy = self.proxies['model']
        model_node = model_proxy.field(entity)
        mouseoverable = entity[MouseOverable]

        into_node = CollisionNode('wecs_mouseoverable')
        into_node.add_solid(mouseoverable.solid)
        into_node.set_from_collide_mask(0x0)
        into_node.set_into_collide_mask(mouseoverable.mask)
        into_node_path = model_node.attach_new_node(into_node)
        into_node_path.set_python_tag('wecs_mouseoverable', entity._uid)

    def exit_filter_mouseoverable(self, entity):
        # FIXME: Undo all the other stuff that accumulated!
        entity[MouseOverable].solid.detach_node()

    def enter_filter_mouseoverable_geometry(self, entity):
        into_node = self.proxies['geometry'].field(entity)

        old_mask = into_node.get_collide_mask()
        new_mask = old_mask | entity[MouseOverableGeometry].mask
        into_node.set_collide_mask(new_mask)
        into_node.find('**/+GeomNode').set_python_tag('wecs_mouseoverable', entity._uid)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['camera']:
            mouse_overing = entity[MouseOveringCamera]
            camera = entity[Camera]
            input = entity[Input]

            # Reset overed entity to None
            mouse_overing.entity = None
            mouse_overing.collision_entry = None

            requested = 'mouse_over' in entity[Input].contexts
            has_mouse = base.mouseWatcherNode.has_mouse()
            if requested and has_mouse:
                # Attach and align testing ray, and run collisions
                self.picker_node_path.reparent_to(camera.camera)
                mpos = base.mouseWatcherNode.get_mouse()
                self.picker_ray.set_from_lens(
                    base.camNode,
                    mpos.getX(),
                    mpos.getY(),
                )
                self.traverser.traverse(camera.camera.get_top())

                # Remember reference to mouseovered entity, if any
                if self.queue.get_num_entries() > 0:
                    self.queue.sort_entries()
                    entry = self.queue.get_entry(0)
                    picked_node = entry.get_into_node_path()
                    picked_uid = picked_node.get_python_tag('wecs_mouseoverable')
                    mouse_overing.entity = picked_uid
                    mouse_overing.collision_entry = entry


class PrintMouseOveredEntity(System):
    entity_filters = {
        'camera': [Camera, Input, MouseOveringCamera],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['camera']:
            mouse_overing = entity[MouseOveringCamera]
            if mouse_overing.entity is not None:
                print(self.world.get_entity(mouse_overing.entity))


@Component()
class Selectable:
    pass


def select_indicator():
    model = base.loader.load_model('models/smiley')
    model.set_sz(0.1)
    return model


@Component()
class Targetable:
    pass


def target_indicator():
    model = base.loader.load_model('models/frowney')
    model.set_scale(0.1, 0.1, 0.25)
    model.set_z(2.1)
    return model


@Component()
class Pointable:
    pass


def point_indicator():
    model = base.loader.load_model('models/jack')
    model.set_scale(0.1)
    return model


@Component()
class UserInterface:
    selected_entity: object = None
    select_indicator: NodePath = field(default_factory=select_indicator)
    target_indicator: NodePath = field(default_factory=target_indicator)
    point_indicator: NodePath = field(default_factory=point_indicator)


class ClickOnEntity(System):
    entity_filters = {
        'cursor': [Input, MouseOveringCamera, UserInterface],
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
        target_entity_uid = entity[MouseOveringCamera].entity
        click_for_select = context.get('select', False)
        click_for_command = context.get('command', False)

        # If we're not pointing at an entity, don't indicate targeting
        if target_entity_uid is None:
            ui.target_indicator.detach_node()
            ui.point_indicator.detach_node()
        # If we *do* point at an entity...
        if target_entity_uid is not None:
            target_entity = self.world.get_entity(target_entity_uid)
            if Targetable in target_entity:
                target_node = target_entity[wecs.panda3d.prototype.Model].node
                ui.target_indicator.reparent_to(target_node)
                ui.point_indicator.detach_node()
            #elif Pointable in target_entity:
            #    entry = entity[MouseOveringCamera].collision_entry
            #    
            #    ui.point_indicator.reparent_to(target_node)
            #    ui.target_indicator.detach_node()
            else:
                ui.target_indicator.detach_node()

        # Was the selected entity removed? Then unselect.
        if ui.selected_entity is not None:
            try:
                self.world.get_entity(ui.selected_entity)
            except NoSuchUID:
                ui.selected_entity = None
                ui.select_indicator.detach_node()

        # Selecting while not pointing at any entity unselects.
        if click_for_select and target_entity_uid is None:
            ui = entity[UserInterface]
            ui.selected_entity = None
            ui.select_indicator.detach_node()
        # Select a selectable entity, unselect if no selectable entity is indicated
        if click_for_select and target_entity_uid is not None:
            target_entity = self.world.get_entity(target_entity_uid)
            if Selectable in target_entity:
                ui.selected_entity = target_entity_uid
                target_node = target_entity[wecs.panda3d.prototype.Model].node
                ui.select_indicator.reparent_to(target_node)
            else:
                ui.selected_entity = None
                ui.select_indicator.detach_node()
        # If we command with no entity at all, unselect.
        if click_for_command and target_entity_uid is None:
            ui.selected_entity = None
            ui.select_indicator.detach_node()
        # But if we point to something...
        if click_for_command and target_entity_uid is not None:
            target_entity = self.world.get_entity(target_entity_uid)
            # Who gets the command?
            if ui.selected_entity:  # The selected entity...
                acting_entity = self.world.get_entity(ui.selected_entity)
            elif BehaviorAI in entity:  # ...or the player entity, if none is selected.
                acting_entity = entity
            else:  # There is no entity to give the command to.
                acting_entity = None
            if acting_entity is not None:
                if Targetable in target_entity:
                    ai = acting_entity[wecs.panda3d.ai.BehaviorAI]
                    if target_entity_uid == ui.selected_entity:
                        action = ['idle']
                    elif ui.selected_entity is None:
                        action = ['walk_to_entity', target_entity_uid]
                        if target_entity_uid == acting_entity._uid:
                            action = ['idle']
                    else:
                        action = ['walk_to_entity', target_entity_uid]
                    ai.behavior = action


class BevaviorInhibitsDirectCharacterControl(System):
    entity_filters = {
        'character': [Input, BehaviorAI, CharacterController],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            behavior = entity[BehaviorAI]
            input = entity[Input]

            if behavior.behavior == ['idle']:
                input.contexts.add('character_movement')
            elif 'character_movement' in input.contexts:
                input.contexts.remove('character_movement')

            
# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras,
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Interface interactions
    MouseOverOnEntity,
    ClickOnEntity,
    # Set inputs to the character controller
    wecs.panda3d.ai.Think,
    BevaviorInhibitsDirectCharacterControl,
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
    # WECS subconsoles
    # wecs.panda3d.cefconsole.UpdateWecsSubconsole,
    # wecs.panda3d.cefconsole.WatchEntitiesInSubconsole,
    # Debug keys (`escape` to close, etc.)
    wecs.panda3d.debug.DebugTools,
]


# Map

game_map = Aspect(
    [
        wecs.panda3d.prototype.Model,
        wecs.panda3d.prototype.Geometry,
        wecs.panda3d.prototype.CollidableGeometry,
        wecs.panda3d.prototype.FlattenStrong,
        MouseOverableGeometry,
        Pointable,
     ],
    overrides={
        wecs.panda3d.prototype.Geometry: dict(file='../../assets/roadE.bam'),
        wecs.panda3d.prototype.CollidableGeometry: dict(
            mask=FALLING_MASK|BUMPING_MASK|CAMERA_MASK,
        ),
    },
)


map_entity = base.ecs_world.create_entity(name="Level geometry")
game_map.add(map_entity)


# Characters, Avatars, Observers

character = Aspect(
    [
        wecs.mechanics.clock.Clock,
        wecs.panda3d.prototype.Model,
        wecs.panda3d.character.CharacterController,
    ],
    overrides={
        wecs.mechanics.clock.Clock: dict(
            clock=lambda: factory(wecs.mechanics.clock.panda3d_clock),
        ),
    },
)


walking = Aspect(
    [
        wecs.panda3d.character.WalkingMovement,
        wecs.panda3d.character.InertialMovement,
        wecs.panda3d.character.BumpingMovement,
        wecs.panda3d.character.FallingMovement,
        wecs.panda3d.character.JumpingMovement,
    ],
    #overrides={wecs.panda3d.character.WalkingMovement:dict(turning_speed=400)}
)


# walking_away_from_camera = Aspect(
#     [
#         wecs.panda3d.character.TurningBackToCameraMovement,
#     ],
# )


avatar = Aspect(
    [
        character,
        wecs.panda3d.prototype.Actor,
        wecs.panda3d.animation.Animation,
        walking,
        MouseOverable,
        Targetable,
    ],
    overrides={
        MouseOverable: dict(solid=CollisionSphere(0, 0, 1, 1)),
    },
)


observer = Aspect(
    [
        character,
        wecs.panda3d.character.FloatingMovement,
    ],
)


# User interface

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


# Interface / AI

pc_mind = Aspect(
    [
        wecs.panda3d.input.Input,
        MouseOveringCamera,
        UserInterface,
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
        Selectable,
    ],
)


# Game Objects, finally!

player = Aspect(
    [
        observer,
        first_person,
        pc_mind,
    ],
)


non_player = Aspect(
    [
        avatar,
        npc_mind,
    ],
)


# WECS' default 3D character is Rebecca, and these are her parameters.

def rebecca_bumper():
    return {
        'bumper': dict(
            shape=CollisionSphere,
            center=Vec3(0.0, 0.0, 1.0),
            radius=0.7,
        ),
    }


def rebecca_lifter():
    return {
        'lifter': dict(
            shape=CollisionSphere,
            center=Vec3(0.0, 0.0, 0.25),
            radius=0.5,
        ),
    }


rebecca = {
    wecs.panda3d.prototype.Geometry: dict(
        file='../../assets/rebecca.bam',
    ),
    wecs.panda3d.prototype.Actor: dict(
        file='../../assets/rebecca.bam',
    ),
    wecs.panda3d.character.BumpingMovement: dict(
        solids=factory(rebecca_bumper),
    ),
    wecs.panda3d.character.FallingMovement: dict(
        solids=factory(rebecca_lifter),
    ),
}


# For the moment, we implement spawn points by just giving coordinates.

spawn_point_1 = {
    wecs.panda3d.prototype.Model: dict(
        post_attach=lambda: wecs.panda3d.prototype.transform(
            pos=Vec3(50, 290, 0),
        ),
    ),
}


spawn_point_2 = {
    wecs.panda3d.prototype.Model: dict(
        post_attach=lambda: wecs.panda3d.prototype.transform(
            pos=Vec3(45, 300, 0),
        ),
    ),
}


spawn_point_3 = {
    wecs.panda3d.prototype.Model: dict(
        post_attach=lambda: wecs.panda3d.prototype.transform(
            pos=Vec3(55, 300, 0),
        ),
    ),
}


spawn_point_air = {
    wecs.panda3d.prototype.Model: dict(
        post_attach=lambda: wecs.panda3d.prototype.transform(
            pos=Vec3(55, 250, 20),
        ),
    ),
}


# Now let's create Rebeccas at the spawn points:

non_player.add(
    base.ecs_world.create_entity(name="Rebecca 1"),
    overrides={
        **rebecca,
        **spawn_point_1,
    },
)


non_player.add(
    base.ecs_world.create_entity(name="Rebecca 2"),
    overrides={
        **rebecca,
        **spawn_point_2,
    },
)


non_player.add(
    base.ecs_world.create_entity(name="Rebecca 3"),
    overrides={
        **rebecca,
        **spawn_point_3,
    },
)


# ...and a disembodied player

player.add(
    base.ecs_world.create_entity(name="Observer"),
    overrides={
        **spawn_point_air,
    },
)
