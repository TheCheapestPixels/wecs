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


# Break this out into something of its own

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
from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.behavior_trees import BehaviorTree
from wecs.panda3d.behavior_trees import IdleWhenDoneTree
from wecs.panda3d.behavior_trees import Action
from wecs.panda3d.behavior_trees import Priorities
from wecs.panda3d.behavior_trees import Chain
from wecs.panda3d.behavior_trees import DebugPrint
from wecs.panda3d.behavior_trees import DebugPrintOnEnter
from wecs.panda3d.behavior_trees import DebugPrintOnReset
from wecs.panda3d.behavior_trees import DoneOnPrecondition
from wecs.panda3d.behavior_trees import FailOnPrecondition
from wecs.panda3d.behavior_trees import DoneTimer


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
        wecs.panda3d.mouseover.MouseOverableGeometry,
        wecs.panda3d.mouseover.Pointable,
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


# There are characters, which are points in space that can be moved
# around using the `CharacterController`, using either player input or
# AI control.

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
# Note that these aren't mutually exclusive. Both can exert control over
# the `CharacterController`. If `Input.contexts` includes
# 'character_movement', AI input is overwritten by player input; If it
# doesn't, it isn't.
# The player interface also can control the NPC AI, using the entity to
# send commands to it if no other entity is selected as recipient.

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


npc_behaviors = lambda: dict(
    #idle=wecs.panda3d.ai.idle,
    idle=IdleWhenDoneTree(
        Chain(
            DoneTimer(
                wecs.panda3d.behavior_trees.timeout(3.0),
                Action(wecs.panda3d.behavior_trees.turn(1.0)),
            ),
            DoneTimer(
                wecs.panda3d.behavior_trees.timeout(3.0),
                Action(wecs.panda3d.behavior_trees.turn(-1.0)),
            ),
        ),
    ),
    walk_to_entity=IdleWhenDoneTree(
        Priorities(
            FailOnPrecondition(
                wecs.panda3d.behavior_trees.is_pointable,
                DoneOnPrecondition(
                    wecs.panda3d.behavior_trees.distance_smaller(1.5),
                    Action(wecs.panda3d.behavior_trees.walk_to_entity),
                ),
            ),
            DoneOnPrecondition(
                wecs.panda3d.behavior_trees.distance_smaller(0.01),
                Action(wecs.panda3d.behavior_trees.walk_to_entity),
            ),
        ),
    ),
)


npc_mind = Aspect(
    [
        wecs.panda3d.ai.BehaviorAI,
        wecs.panda3d.mouseover.Selectable,
    ],
    overrides={
        wecs.panda3d.ai.BehaviorAI: dict(
            behavior=['idle'],
            behaviors=lambda: npc_behaviors(),
        ),
    },
)


# Game Objects, finally!
# An observer is a disembodied, player-controlled character.
# A player_character is a player-controlled avatar
# A non_player_character is an AI-controlled avatar.

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
    MouseOverable: dict(
        solid=CollisionSphere(0, 0, 1, 1),
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

non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca 1"),
    overrides={
        **rebecca,
        **spawn_point_1,
    },
)


non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca 2"),
    overrides={
        **rebecca,
        **spawn_point_2,
    },
)


non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca 3"),
    overrides={
        **rebecca,
        **spawn_point_3,
    },
)


# ...and a player

observer.add(
    base.ecs_world.create_entity(name="Observer"),
    overrides={
        **spawn_point_air,
    },
)

# To be created as a player character, instead just do this:
# 
# player_character.add(
#     base.ecs_world.create_entity(name="Playerbecca"),
#     overrides={
#         **rebecca,
#         **spawn_point_air,
#     },
# )
