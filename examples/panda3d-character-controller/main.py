#!/usr/bin/env python

import sys

from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import NodePath

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
        panda3d.AddRemoveCharacterHull,
        panda3d.DetermineTimestep,
        panda3d.ClearMoveChecker,
        panda3d.CheckMovementSensors,
        panda3d.CheckNullMovement,
        #panda3d.PrintMovements,
        panda3d.AcceptInput,
        panda3d.UpdateCharacter,
        panda3d.UpdateCameras,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    character = base.ecs_world.create_entity(
        panda3d.Clock(clock=globalClock),
        panda3d.Position(value=Point3(0, 0, 0)),
        # panda3d.Model(model_name='models/smiley'),
        panda3d.Model(model_name='gal.bam'),
        # panda3d.Model(node=NodePath('spectator')),
        panda3d.Scene(node=base.render),
        # Movement-related components
        panda3d.MoveChecker(
            debug=True,
        ),
        panda3d.CharacterHull(
            center=Vec3(0.0, 0.0, 0.85),
            radius=0.85,
            debug=True,
        ),
        panda3d.NullMovement(),
        # Others
        panda3d.CharacterController(
            max_move_x=100,
            max_move_y=100,
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
