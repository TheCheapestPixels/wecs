#!/usr/bin/env python

import sys

from panda3d.core import Point3
from panda3d.core import NodePath

from wecs.panda3d import ECSShowBase as ShowBase
from wecs import panda3d


if __name__ == '__main__':
    ShowBase()
    base.disable_mouse()
    base.accept('escape', sys.exit)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)

    system_types = [
        panda3d.LoadModels,
        panda3d.DetermineTimestep,
        panda3d.AcceptInput,
        panda3d.UpdateCharacter,
        panda3d.UpdateCameras,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    character = base.ecs_world.create_entity(
        panda3d.Clock(clock=globalClock),
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(node=NodePath('spectator')),
        panda3d.Scene(node=base.render),
        panda3d.CharacterController(),
        # panda3d.ThirdPersonCamera(camera=base.cam),
        panda3d.FirstPersonCamera(camera=base.cam),
        panda3d.Input(),
    )

    static_level = base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(model_name='models/environment'),
        panda3d.Scene(node=base.render),
    )

    base.run()
