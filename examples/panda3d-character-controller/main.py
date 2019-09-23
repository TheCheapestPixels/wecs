#!/usr/bin/env python

import sys

from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionSphere

from wecs.core import Component
from wecs.panda3d import ECSShowBase as ShowBase
from wecs import panda3d


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
    base.disable_mouse()
    base.accept('escape', sys.exit)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)

    system_types = [
        LoadMapsAndActors,
        panda3d.DetermineTimestep,
        # What movements *can* the character make right now?
        panda3d.CheckMovementSensors,
        # What movement does the player choose?
        panda3d.AcceptInput,
        panda3d.UpdateCharacter,
        panda3d.PredictFalling,
        panda3d.CheckCollisionSensors,
        panda3d.ExecuteJumping,
        panda3d.ExecuteFalling,
        panda3d.ExecuteMovement,
        panda3d.UpdateCameras,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    character = base.ecs_world.create_entity(
        panda3d.Clock(clock=globalClock),
        panda3d.Position(value=Point3(0, 0, 0)),
        # panda3d.Model(node=NodePath('spectator')),
        # panda3d.Model(model_name='models/smiley'),
        panda3d.Model(model_name='rebecca.bam'),
        panda3d.Scene(node=base.render),
        # Movement-related components
        panda3d.MovementSensors(
            tag_name='movement_sensors',
            # debug=True,
        ),
        panda3d.CollisionSensors(
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
        panda3d.FallingMovement(
            gravity=Vec3(0, 0, -9.81)
        ),
        panda3d.JumpingMovement(
            impulse=Vec3(0, 0, 6),
        ),
        # Others
        panda3d.CharacterController(
            max_move_x=20,
            max_move_y=20,
        ),
        panda3d.ThirdPersonCamera(
            camera=base.cam,
            height=2.0,
            focus_height=1.8,
        ),
        # panda3d.FirstPersonCamera(camera=base.cam),
        panda3d.Input(),
    )

    static_level = base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(model_name='roadD.bam'),
        panda3d.Scene(node=base.render),
        Map(),
    )

    base.run()
