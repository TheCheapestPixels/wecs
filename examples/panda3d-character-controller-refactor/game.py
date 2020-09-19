from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import CollisionSphere

# from wecs import cefconsole
import wecs
from wecs.core import ProxyType
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.panda3d import debug


m_proxy = {
    'model': ProxyType(wecs.panda3d.prototype.Model, 'node'),
}
cn_proxy = {
    'character_node': ProxyType(wecs.panda3d.prototype.Model, 'node'),
    'scene_node': ProxyType(wecs.panda3d.prototype.Model, 'parent'),
}
a_proxy = {
    'actor': ProxyType(wecs.panda3d.prototype.Actor, 'node'),
}


# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras(proxies=m_proxy),
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Character controller
    wecs.panda3d.character.UpdateCharacter(proxies=cn_proxy),
    wecs.panda3d.character.Walking,
    wecs.panda3d.character.Bumping(proxies=cn_proxy),
    wecs.panda3d.character.Falling(proxies=cn_proxy),
    wecs.panda3d.character.ExecuteMovement(proxies=cn_proxy),
    # Animation
    wecs.panda3d.animation.AnimateCharacter(proxies=a_proxy),
    wecs.panda3d.animation.Animate(proxies=a_proxy),
    # Camera
    wecs.panda3d.camera.ReorientObjectCentricCamera,
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
        wecs.panda3d.character.BumpingMovement,
        wecs.panda3d.character.FallingMovement,
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


player = Aspect(
    [
        avatar,
        animated_appearance,
        pc_mind,
        third_person,
    ],
)


non_player = Aspect(
    [
        avatar,
        animated_appearance,
    ],
)


# WECS' default character is Rebecca, and these are her parameters.

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


static_rebecca = {
    wecs.panda3d.prototype.Geometry: dict(file='../../assets/rebecca.bam'),
    wecs.panda3d.character.BumpingMovement: dict(solids=factory(rebecca_bumper)),
    wecs.panda3d.character.FallingMovement: dict(solids=factory(rebecca_lifter)),
}


animated_rebecca = {
    wecs.panda3d.prototype.Geometry: dict(file='../../assets/rebecca.bam'),
    wecs.panda3d.prototype.Actor: dict(file='../../assets/rebecca.bam'),
    wecs.panda3d.character.BumpingMovement: dict(solids=factory(rebecca_bumper)),
    wecs.panda3d.character.FallingMovement: dict(solids=factory(rebecca_lifter)),
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


# Now let's ceate a Rebecca at the spawn point:

player.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={**animated_rebecca, **spawn_point_1},
)


non_player.add(
    base.ecs_world.create_entity(name="Rebecca"),
    overrides={**animated_rebecca, **spawn_point_2},
)
