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
from wecs.aspects import Aspect
from wecs.aspects import factory
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
    panda3d.CollideCamerasWithTerrain,
]


def populate_world():
    # An ontology of aspects
    character = Aspect([panda3d.Clock, panda3d.Position, panda3d.Scene, panda3d.CharacterController],
                       overrides = {
                           panda3d.Clock: dict(clock=globalClock),
                           panda3d.Scene: dict(node=base.render),
                       }
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
    walking = Aspect([panda3d.WalkingMovement, panda3d.CrouchingMovement, panda3d.SprintingMovement,
                      panda3d.InertialMovement, panda3d.BumpingMovement, panda3d.FallingMovement,
                      panda3d.JumpingMovement],
                     overrides = {
                         panda3d.InertialMovement: dict(acceleration=30.0, rotated_inertia=0.5),
                         panda3d.BumpingMovement: dict(solids=factory(lambda:rebecca_bumper())),
                         panda3d.FallingMovement: dict(solids=factory(lambda:rebecca_lifter())),
                         panda3d.JumpingMovement: dict(impulse=factory(lambda: Vec3(0, 0, 6))),
                     },
    )

    avatar = Aspect([character, walking, panda3d.Model, mechanics.Stamina],
                    overrides={panda3d.Model: dict(model_name='rebecca.bam')})

    def spectator_bumper():
        return dict(
            solids={
                'bumper': dict(
                    shape=CollisionSphere,
                    center=Vec3(0.0, 0.0, 0.0),
                    radius=1.0,
                ),
            },
        )
    spectator = Aspect([character, panda3d.Model, panda3d.FloatingMovement, panda3d.BumpingMovement],
                       overrides={
                           panda3d.Model: dict(node=factory(lambda:NodePath('spectator'))),
                           panda3d.BumpingMovement: dict(solids=factory(lambda:spectator_bumper())),
                       },
    )
    
    pc_mind = Aspect([panda3d.Input])

    npc_mind = Aspect([panda3d.ConstantCharacterAI],
                 overrides={
                     panda3d.ConstantCharacterAI: dict(
                         move=factory(lambda:Vec3(0.0, 0.25, 0.0)),
                         heading=-0.5,
                     ),
                 },
    )
    
    first_person = Aspect([panda3d.FirstPersonCamera],
                          overrides={panda3d.FirstPersonCamera: dict(camera=base.cam)})

    third_person = Aspect([panda3d.TurntableCamera, panda3d.TurningBackToCameraMovement,
                           panda3d.CollisionZoom, panda3d.ThirdPersonCamera],
                          overrides={
                              panda3d.ThirdPersonCamera: dict(
                                  camera=base.cam,
                                  focus_height=1.8,
                              ),
                          },
    )

    player_character = Aspect([avatar, pc_mind, third_person])
    non_player_character = Aspect([avatar, npc_mind])

    game_map = Aspect([panda3d.Position, panda3d.Model, panda3d.Scene, Map],
                      overrides={
                          panda3d.Position: dict(value=factory(lambda:Point3(0, 0, 0))),
                          panda3d.Model: dict(model_name='roadE.bam'),
                          panda3d.Scene: dict(node=base.render),
                      },
    )

    ### The map, the player character, an NPC
    game_map.add(base.ecs_world.create_entity())
    player_character.add(
        base.ecs_world.create_entity(),
        overrides={panda3d.Position: dict(value=Point3(50, 295, 0))},
    )
    non_player_character.add(
        base.ecs_world.create_entity(),
        overrides={panda3d.Position: dict(value=Point3(50, 300, 0))},
    )
    non_player_character.add(
        base.ecs_world.create_entity(),
        overrides={
            panda3d.Position: dict(value=Point3(55, 300, 0)),
            panda3d.ConstantCharacterAI: dict(
                move=Vec3(0.0, 0.75, 0.0),
                heading=-0.1,
            ),
        },
    )


if __name__ == '__main__':
    # Application Basics
    ShowBase()
    #simplepbr.init(max_lights=1)
    base.disable_mouse()

    # Handy Helpers: esc to quit, f11 for pdb, f12 for pstats
    base.accept('escape', sys.exit)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)
    def pstats():
        base.pstats = True
        PStatClient.connect()
    base.accept('f12', pstats)

    # Set up the world:
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)
    populate_world()

    # And here we go...
    base.run()
