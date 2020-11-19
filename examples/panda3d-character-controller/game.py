from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import CollisionSphere

# from wecs import cefconsole
import wecs
from wecs.core import ProxyType
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.panda3d import debug

from wecs.panda3d.constants import FALLING_MASK
from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import CAMERA_MASK


# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras,
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Character AI
    wecs.panda3d.ai.Think,
    # Character controller
    wecs.panda3d.character.UpdateCharacter,
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
     ],
    overrides={
        wecs.panda3d.prototype.Geometry: dict(file='roadE.bam'),
        wecs.panda3d.prototype.CollidableGeometry: dict(
            mask=FALLING_MASK|BUMPING_MASK|CAMERA_MASK,
        ),
    },
)


map_entity = base.ecs_world.create_entity(name="Level geometry")
game_map.add(map_entity)


# Player
#
# * A player is character is an avatar with a PC mind, an animated
#   appearance, and a third person camera.
#   * An avatar is a walking character.
#     * A character is a `CharacterController` with a `Clock` and a
#       `Model`.
#     * An entity that is walking performs `WalkingMovement`,
#       `BumpingMovement`, and `FallingMovement`.
#   * A PC mind means that this entity's "AI" is user `Input`.
#   * A third person camera is a `Camera` in `ObjectCentricCameraMode`.
#   * An animated appearance is simply an `Actor`.
#
# Note how the Aspects form a tree that eventually ends in component
# types, and that no part of the tree is overlapping with any other,
# meaning that each component type appears in its leafs only once.

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
)


walking_away_from_camera = Aspect(
    [
        wecs.panda3d.character.TurningBackToCameraMovement,
    ],
)


avatar = Aspect(
    [
        character,
        walking,
    ],
)


third_person = Aspect(
    [
        wecs.panda3d.camera.Camera,
        wecs.panda3d.camera.ObjectCentricCameraMode,
        wecs.panda3d.camera.CollisionZoom,
    ],
)


pc_mind = Aspect(
    [
        wecs.panda3d.input.Input,
    ],
    overrides={
        wecs.panda3d.input.Input: dict(
            contexts=[
                'character_movement',
                'camera_movement',
            ],
        ),
    },
)


npc_mind_constant = Aspect(
    [
        wecs.panda3d.ai.BehaviorAI,
        wecs.panda3d.ai.ConstantCharacterAI,
    ],
    overrides={
        wecs.panda3d.ai.ConstantCharacterAI: dict(
            move=Vec3(0, 0.2, 0),
            heading=1.0,
        ),
        wecs.panda3d.ai.BehaviorAI: dict(
            behavior=['constant'],
        ),
    },
)


static_appearance = Aspect(
    [
        wecs.panda3d.prototype.Geometry,
    ],
)


animated_appearance = Aspect(
    [
        wecs.panda3d.prototype.Actor,
        wecs.panda3d.animation.Animation,
    ],
)


sprite_appearance = Aspect(
    [
        wecs.panda3d.prototype.Sprite,
        wecs.panda3d.prototype.Billboard,
    ],
)


player = Aspect(
    [
        avatar,
        animated_appearance,
        pc_mind,
        third_person,
        walking_away_from_camera,
    ],
)


non_player = Aspect(
    [
        avatar,
        animated_appearance,
        npc_mind_constant,
    ],
)


non_player_sprite = Aspect(
    [
        avatar,
        sprite_appearance,
        npc_mind_constant,
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


# WECS' default 2D character is Mr. Man

mrman = {
    wecs.panda3d.prototype.Sprite: dict(
        image_name="../../assets/mrman.png",
        sprite_height=16,
        sprite_width=16,
        animations={
            "walking": [6, 7, 8, 9, 10, 11]
        },
        animation="walking",
        framerate=15,
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
            pos=Vec3(60, 290, 0),
        ),
    ),
}


spawn_point_3 = {
    wecs.panda3d.prototype.Model: dict(
        post_attach=lambda: wecs.panda3d.prototype.transform(
            pos=Vec3(70, 290, 0),
        ),
    ),
}


# Now let's ceate a Rebecca at the spawn point:

player.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={**rebecca, **spawn_point_1},
)


non_player.add(
    base.ecs_world.create_entity(name="Rebecca"),
    overrides={
        **rebecca,
        **spawn_point_2,
    },
)


non_player_sprite.add(
    base.ecs_world.create_entity(name="Mr. Man"),
    overrides={
        **mrman,
        **spawn_point_3,
    },
)
