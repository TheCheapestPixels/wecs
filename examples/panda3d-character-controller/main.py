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


@Component()
class Map:
    pass


class LoadMapsAndActors(panda3d.LoadModels):
    def post_load_hook(self, node, entity):
        if Map in entity:
            node.flatten_strong()
            node.set_collide_mask(1<<0)


if __name__ == '__main__':
    ShowBase()
    # simplepbr.init(max_lights=1)
    base.disable_mouse()
    base.cTrav = False

    base.accept('escape', sys.exit)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)
    def pstats():
        base.pstats = True
        PStatClient.connect()
    base.accept('f12', pstats)

    system_types = [
        LoadMapsAndActors,
        panda3d.DetermineTimestep,
        # How does the character want to move?
        panda3d.AcceptInput,  # What movement does the player choose?
        panda3d.UpdateCharacter,  # Determine intended movement.
        mechanics.UpdateStamina, # Disables input based on current stamina
        panda3d.UpdateSpeed, # Set speed according to input
        panda3d.Accelerating, # Movement is accumulated instead of instant.
        # The following systems adjust the intended movement
        panda3d.Bumping, # FIXME: Stub for bumping into things
        panda3d.Falling, # Falling, and standing on the ground
        panda3d.Jumping, # Impart upward impulse. Executed by falling.
        # Turn intention into actual movement
        panda3d.ExecuteMovement,
        # We're done with character movement now.
        panda3d.UpdateCameras,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    character = base.ecs_world.create_entity(
        panda3d.Clock(clock=globalClock),
        panda3d.Position(value=Point3(50, 295, 0)),
        # panda3d.Model(node=NodePath('spectator')),
        # panda3d.Model(model_name='models/smiley'),
        panda3d.Model(model_name='rebecca.bam'),
        panda3d.Scene(node=base.render),
        # Movement-related components
        panda3d.MovementSensors(
            tag_name='movement_sensors',
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
                    debug=True,
                ),
            },
            debug=True,
        ),
        panda3d.FallingMovement(
            gravity=Vec3(0, 0, -9.81),
            solids={
                'lifter': dict(
                    shape=CollisionSphere,
                    center=Vec3(0.0, 0.0, 0.25),
                    radius=0.5,
                    debug=True,
                ),
            },
            # debug=True,
        ),
        panda3d.JumpingMovement(
            impulse=Vec3(0, 0, 6),
        ),
        panda3d.SprintingMovement(),
        panda3d.WalkingMovement(),
        panda3d.CrouchingMovement(),
        panda3d.AirMovement(),
        panda3d.AcceleratingMovement(),
        # Others
        mechanics.Stamina(),
        panda3d.CharacterController(),
        panda3d.ThirdPersonCamera(camera=base.cam),
        # panda3d.FirstPersonCamera(camera=base.cam),
        panda3d.Input(),
    )

    static_level = base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(model_name='roadE.bam'),
        panda3d.Scene(node=base.render),
        Map(),
    )

    base.run()
