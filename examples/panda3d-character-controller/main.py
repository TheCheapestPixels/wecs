#!/usr/bin/env python

import sys

from panda3d.core import Point3
from panda3d.core import Vec2, Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionSphere
from panda3d.core import CollisionCapsule
from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

# import simplepbr

from wecs.core import Component
from wecs.panda3d import ECSShowBase as ShowBase
from wecs import panda3d
from wecs import mechanics


# Ignore this for the moment please; It means "This entity's model can be collided into".
@Component()
class Map:
    pass


# Ignore this too; It makes the map collidable.
class LoadMapsAndActors(panda3d.LoadModels):
    def post_load_hook(self, node, entity):
        if Map in entity:
            node.flatten_strong()
            node.set_collide_mask(1<<0)


# Each frame, run these systems. This defines the game itself.
system_types = [
    # Self-descriptive...
    LoadMapsAndActors,
    # How long is this frame? Update all clocks.
    panda3d.DetermineTimestep,
    # What movement does the player intend? Set it on character
    # controller (as translation and rotation) in normalized
    # range ([-1; 1]), ignoring time scaling.
    panda3d.AcceptInput, # Input from player
    panda3d.Think, # Input from AIs
    mechanics.UpdateStamina,
    panda3d.TurningBackToCamera,
    # Scale inputs by frame time, making them "Intended movement in this
    # frame."
    panda3d.UpdateCharacter,
    # The following systems adjust the intended movement
    panda3d.Floating, # Scale speed for floating
    panda3d.Walking, # Scale speed for walk / run / crouch / sprint
    panda3d.Inertiing, # Clamp movement speed delta by inertia
    panda3d.Bumping, # Bump into things (and out again).
    panda3d.Falling, # Fall, or stand on the ground.
    panda3d.Jumping, # Impart upward impulse.
    # Turn intention into actual movement
    panda3d.ExecuteMovement,
    # We're done with character movement, now adjust the cameras.
    panda3d.UpdateCameras,
    panda3d.CameraCollisions,
]


### An Ontology of Characters
#
# To manage modes that a character can be in, we define sets of
# components to be added or removed in state changes.
# * character: Game definition of a character; Something controllable somewhere.
# * avatar: A character with a body that walks around.
# * spectator: A disembodied character that flies.
# * player: A character that accepts keyboard input
# * npc: A character that has AI for input
# * first_person: A player with 1st person view
# * third_person: A player with 3rd person view
#
# So when the player is in avatar mode, the active sets are character, avatar,
# player, third_person. Switching to spectator mode removes avatar and
# third_person, and adds spectator and first_person. Switching back, the same in
# reverse.
#
# The goal here is also to have a mechanism to compose entities quickly. Need an
# NPC? Use an avatar and add an AI component, done. This is currently far from
# inplemented, since the sets here are ones of component instances. What they
# should be is some kind of copyable dictionaries with default values that get
# stuffed into components; Some kind of factories. But we *also* need actual
# instances, since some component instances will use resources that shareable
# (displays and input devices), so there has to be exactly one instance per
# type and resource. Any idea for an API that makes this kind of composition
# effortless? It should also make it easy to provide overrides for default
# values.

def character():
    return set([
        panda3d.Clock(clock=globalClock),
        panda3d.Position(value=Point3(50, 295, 0)),
        panda3d.Scene(node=base.render),
        panda3d.CharacterController(),
    ])
def avatar():
    return set([
        panda3d.Model(model_name='rebecca.bam'),
        panda3d.WalkingMovement(),
        panda3d.CrouchingMovement(),
        panda3d.SprintingMovement(),
        panda3d.InertialMovement(
            acceleration=30.0,
            rotated_inertia=0.5,
        ),
        panda3d.BumpingMovement(
            solids={
                # 'bumper': dict(
                #     shape=CollisionCapsule,
                #     end_a=Vec3(0.0, 0.0, 0.7),
                #     end_b=Vec3(0.0, 0.0, 1.1),
                #     radius=0.6,
                #     debug=True,
                # ),
                'bumper': dict(
                    shape=CollisionSphere,
                    center=Vec3(0.0, 0.0, 1.0),
                    radius=0.7,
                    # debug=True,
                ),
            },
            # debug=True,
        ),
        panda3d.FallingMovement(
            gravity=Vec3(0, 0, -9.81),
            solids={
                'lifter': dict(
                    shape=CollisionSphere,
                    center=Vec3(0.0, 0.0, 0.25),
                    radius=0.5,
                    # debug=True,
                ),
            },
            # debug=True,
        ),
        panda3d.JumpingMovement(
            impulse=Vec3(0, 0, 6),
        ),
        mechanics.Stamina(),
    ])
def spectator():
    return set([
        panda3d.Model(model_name='models/smiley'),
        # panda3d.Model(node=NodePath('spectator')),
        panda3d.FloatingMovement(),
        panda3d.BumpingMovement(
            solids={
                'bumper': dict(
                    shape=CollisionSphere,
                    center=Vec3(0.0, 0.0, 0.0),
                    radius=1.0,
                ),
            },
        ),
    ])
def player():
    return set([
        panda3d.Input(),
    ])
def npc():
    return set([
        panda3d.ConstantCharacterAI(
            move=Vec3(0.0, 0.75, 0.0),
            heading=-0.1,
        ),
    ])
def first_person():
    return set([
        panda3d.FirstPersonCamera(camera=base.cam),
    ])
def third_person():
    return set([
        panda3d.ThirdPersonCamera(
            camera=base.cam,
            focus_height=1.8,
        ),
        panda3d.TurntableCamera(),
        panda3d.TurningBackToCameraMovement(),
        panda3d.CameraCollision(),
    ])


if __name__ == '__main__':
    ### Application Basics
    ShowBase()
    # simplepbr.init(max_lights=1)
    base.disable_mouse()

    ### Handy Helpers: esc to quit, f11 for pdb, f12 for pstats
    base.accept('escape', sys.exit)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)
    def pstats():
        base.pstats = True
        PStatClient.connect()
    base.accept('f12', pstats)

    ### Set up systems
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    ### Game world
    base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(model_name='roadE.bam'),
        panda3d.Scene(node=base.render),
        Map(),
    )

    ### Player Character
    base.ecs_world.create_entity(
        *set.union(
            character(),
            avatar(),
            # spectator(),
            player(),
            # npc(),
            third_person(),
            # first_person(),
        )
    )

    ### Non-Player Character: For when the archetyping stuff described above works
    #base.ecs_world.create_entity(
    #    *set.union(
    #        character(),
    #        avatar(),
    #        npc(),
    #    )
    #)

    ### Run
    base.run()
