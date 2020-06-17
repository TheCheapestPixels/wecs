#!/usr/bin/env python

import sys

from panda3d.core import Vec3
from panda3d.core import Point3
from panda3d.core import VBase3
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.panda3d import ECSShowBase as ShowBase
from wecs import panda3d


if __name__ == '__main__':
    ShowBase()
    base.disable_mouse()
    base.accept('escape', sys.exit)
    base.cam.set_pos(0, -5, 0)

    system_types = [
        panda3d.SetUpPhysics,
        panda3d.SetupModels,
        panda3d.ManageGeometry,
        panda3d.DetermineTimestep,
        panda3d.DoPhysics,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    # We don't use the default world here to set gravity manually.
    bullet_world = BulletWorld()
    bullet_world.set_gravity(Vec3(0, 0, -9.81))
    world = base.ecs_world.create_entity(
        panda3d.PhysicsWorld(
            world=bullet_world,

        ),
        panda3d.Scene(node=base.render),
    )

    bullet_body = BulletRigidBodyNode()
    bullet_body.set_linear_sleep_threshold(0)
    bullet_body.set_angular_sleep_threshold(0)
    bullet_body.set_mass(1.0)
    ball = base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Geometry(file='ball.bam'),
        panda3d.PhysicsBody(
            body=bullet_body,
            world=world._uid,
            scene=world._uid,
        ),
    )

    base.run()
