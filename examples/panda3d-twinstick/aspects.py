from panda3d.core import Vec3
from panda3d.core import CollisionSphere

import wecs

from wecs.aspects import Aspect
from wecs.aspects import factory

from wecs.panda3d.constants import FALLING_MASK
from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import CAMERA_MASK

import behaviors


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
        wecs.panda3d.prototype.Geometry: dict(
            file='../../assets/roadE.bam',
        ),
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
        wecs.panda3d.character.CharacterController: dict(
            gravity=Vec3(0, 0, -30),
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
    ],
    overrides={
        wecs.panda3d.character.JumpingMovement:dict(
            impulse=Vec3(0, 0, 10),
        ),
    }
)


avatar = Aspect(
    [
        character,
        animated,
        walking,
        wecs.panda3d.mouseover.MouseOverable,
        wecs.panda3d.mouseover.Targetable,
    ],
    overrides={
        wecs.panda3d.character.WalkingMovement: dict(
            turning_speed=40.0,
            #turning_speed=540.0,
        ),
    },
)


third_person = Aspect(
    [
        wecs.panda3d.camera.Camera,
        wecs.panda3d.camera.ObjectCentricCameraMode,
        wecs.panda3d.camera.CollisionZoom,
        wecs.panda3d.character.AutomaticTurningMovement,
        wecs.panda3d.character.CameraReorientedInput,
        wecs.panda3d.character.TwinStickMovement,
    ],
    overrides={
        wecs.panda3d.camera.ObjectCentricCameraMode: dict(
            turning_speed=180.0,
            initial_pitch=-30.0,
            distance=30.0,
        ),
    },
)


pc_mind = Aspect(
    [
        wecs.panda3d.input.Input,
    ],
    overrides={
        wecs.panda3d.input.Input: dict(
            contexts={
                'character_movement',
                'character_direction',
            },
        ),
    },
)


npc_behaviors = lambda: dict(
    idle=behaviors.idle(),
)


npc_mind = Aspect(
    [
        wecs.panda3d.ai.BehaviorAI,
    ],
    overrides={
        wecs.panda3d.ai.BehaviorAI: dict(
            behavior=['idle'],
            behaviors=lambda: npc_behaviors(),
        ),
    },
)


player_character = Aspect(
    [
        avatar,
        third_person,
        pc_mind,
        #npc_mind,
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
    wecs.panda3d.mouseover.MouseOverable: dict(
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
