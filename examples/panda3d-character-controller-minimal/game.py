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


# Each frame, run these systems. This defines the game itself.
system_types = [
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras(proxies=m_proxy),
    wecs.mechanics.clock.DetermineTimestep,
    wecs.panda3d.character.UpdateCharacter(proxies=cn_proxy),
    wecs.panda3d.character.Walking,
    wecs.panda3d.character.Bumping(proxies=cn_proxy),
    wecs.panda3d.character.Falling(proxies=cn_proxy),
    wecs.panda3d.character.ExecuteMovement(proxies=cn_proxy),
    wecs.panda3d.camera.ReorientObjectCentricCamera,
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

character = Aspect(
    [
        wecs.mechanics.clock.Clock,
        wecs.panda3d.prototype.Model,
        wecs.panda3d.prototype.Geometry,
        wecs.panda3d.character.CharacterController,
    ],
    overrides={
        wecs.mechanics.clock.Clock: dict(
            clock=lambda: factory(wecs.mechanics.clock.panda3d_clock),
        ),
    },
)


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


walking = Aspect(
    [
        wecs.panda3d.character.WalkingMovement,
        wecs.panda3d.character.BumpingMovement,
        wecs.panda3d.character.FallingMovement,
    ],
    overrides={
        wecs.panda3d.character.BumpingMovement: dict(solids=factory(rebecca_bumper)),
        wecs.panda3d.character.FallingMovement: dict(solids=factory(rebecca_lifter)),
    },
)


avatar = Aspect(
    [
        character,
        walking,
    ],
    overrides={
        wecs.panda3d.prototype.Geometry: dict(file='../../assets/rebecca.bam'),
    },
)


third_person = Aspect([
    wecs.panda3d.camera.Camera,
    wecs.panda3d.camera.ObjectCentricCameraMode,
])


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


player_character = Aspect([avatar, pc_mind, third_person])


player_character.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={
        wecs.panda3d.prototype.Model: dict(
            post_attach=lambda: wecs.panda3d.prototype.transform(
                pos=Vec3(50, 290, 0),
            ),
        ),
    },
)
