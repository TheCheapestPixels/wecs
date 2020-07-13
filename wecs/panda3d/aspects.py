from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionSphere

from wecs.aspects import Aspect
from wecs.aspects import factory

from wecs.mechanics import clock
from wecs import panda3d as wp3d

# An ontology of aspects:
# * Controllable beings on the map
#   `character`s are controllable entities with a "physical" presence (a Model)
#   `walking` is the ability to move around and interact with the map
#   To be `animated` means to be an Actor and Animated.
#   An `avatar` is a character that can walk and is animated.
#   A `spectator` is a character that floats and bumps into the map.
# * Things that control beings
#   `pc_mind` represents the input from the neural network between the player's ears.
#   `npc_mind` is a mind that executes a constant movement
# * Things that see the world
#   `first_person` is a first person camera
#   `third_person` is, unsurprisingly, a third person camera (with a few features).
# * Abstractions that are actually useful
#   The `player_character` is an `avatar` controlled by a `pc_mind` and seen through
#     the `third_person` camera.
#   A `non_player_character` is an `avatar` controlled by an `npc_mind`
#   A `game_map` is a model that you can bump / fall into.

character = Aspect(
    [
        clock.Clock,
        wp3d.Position,
        wp3d.Scene,
        wp3d.CharacterController,
        wp3d.Model,
        wp3d.Geometry,
    ],
    overrides={
        clock.Clock: dict(clock=clock.panda3d_clock),
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
        wp3d.WalkingMovement,
        wp3d.CrouchingMovement,
        wp3d.SprintingMovement,
        wp3d.InertialMovement,
        wp3d.BumpingMovement,
        wp3d.FallingMovement,
        wp3d.JumpingMovement,
    ],
    overrides={
        wp3d.BumpingMovement: dict(solids=factory(rebecca_bumper)),
        wp3d.FallingMovement: dict(solids=factory(rebecca_lifter)),
    },
)
animated = Aspect([wp3d.Actor, wp3d.Animation])
avatar = Aspect([character, walking, animated],
                overrides={
                    wp3d.Actor: dict(file='../../assets/rebecca.bam'),
                })


def spectator_bumper():
    return dict(
        solids={
            'bumper': dict(
                shape=CollisionSphere,
                center=Vec3(0.0, 0.0, 0.0),
                radius=0.1,
            ),
        },
    )


spectator = Aspect(
    [
        character,
        wp3d.FloatingMovement,
        wp3d.BumpingMovement,
    ],
    overrides={
        wp3d.Model: dict(
            node=factory(lambda: NodePath('spectator')),
        ),
        wp3d.BumpingMovement: dict(
            solids=factory(spectator_bumper),
        ),
    },
)

pc_mind = Aspect([wp3d.Input],
                 overrides={
                     wp3d.Input: dict(contexts=[
                         'character_movement',
                         'camera_movement',
                         'clock_control',
                     ]),
                 },
                 )
npc_mind_constant = Aspect([wp3d.ConstantCharacterAI])
npc_mind_brownian = Aspect([wp3d.BrownianWalkerAI])

first_person = Aspect([
    wp3d.Camera,
    wp3d.MountedCameraMode,
])
third_person = Aspect([
    wp3d.Camera,
    wp3d.ObjectCentricCameraMode,
    wp3d.TurningBackToCameraMovement,
    wp3d.CollisionZoom,
])

player_character = Aspect([avatar, pc_mind, third_person])
non_player_character = Aspect([avatar, npc_mind_constant])
