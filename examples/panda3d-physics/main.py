#!/usr/bin/env python

import sys
import random

from panda3d.core import Vec3
from panda3d.core import Point3
from panda3d.core import VBase3
from panda3d.core import TransformState
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletBoxShape

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.mechanics import clock
from wecs.panda3d import ECSShowBase
from wecs.panda3d import prototype


creation_interval = 0.3
ball_size = 0.2
wall_height = 0.8
base_size = 1.0
debug = True


def add_smiley(world, bullet_body):
    x = random.random() - 0.5
    y = random.random() - 0.5
    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=prototype.transform(pos=Vec3(x, y, 1)),
        ),
        prototype.Geometry(
            file='models/smiley',
            post_attach=prototype.transform(
                scale=ball_size,
                component_type=prototype.Geometry,
            ),
        ),
        prototype.PhysicsBody(
            body=bullet_body,
            world=world._uid,
        ),
    )


def add_panda(world, bullet_body):
    x = random.random() - 0.5
    y = random.random() - 0.5
    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=prototype.transform(pos=Vec3(x, y, 1)),
        ),
        prototype.Actor(
            file="models/panda-model",
            animations={"walk": "models/panda-walk4"},
            animation="walk",
            post_attach=prototype.transform(
                pos=Vec3(0, 0, -0.1),
                scale=ball_size * 0.003,
                component_type=prototype.Actor,
            ),
        ),
        prototype.PhysicsBody(
            body=bullet_body,
            world=world._uid,
        ),
    )


def add_mr_man_static(world, bullet_body):
    x = random.random() - 0.5
    y = random.random() - 0.5
    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=prototype.transform(pos=Vec3(x, y, 1)),
        ),
        clock.Clock(clock=clock.panda3d_clock),
        prototype.Sprite(
            image_name='../../assets/mrman.png',
            sprite_height=16,
            sprite_width=16,
            update=True,
            post_attach=prototype.transform(
                scale=ball_size,
                component_type=prototype.Sprite,
            ),
        ),
        prototype.PhysicsBody(
            body=bullet_body,
            world=world._uid,
        ),
    )


def add_mr_man_dynamic(world, bullet_body):
    x = random.random() - 0.5
    y = random.random() - 0.5
    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=prototype.transform(pos=Vec3(x, y, 1)),
        ),
        clock.Clock(clock=clock.panda3d_clock),
        prototype.Sprite(
            image_name='../../assets/mrman.png',
            sprite_height=16,
            sprite_width=16,
            update=True,
            animations={
                'walking': [6, 7, 8, 9, 10, 11]
            },
            animation='walking',
            framerate=15,
            loop=True,
            post_attach=prototype.transform(
                scale=ball_size,
                component_type=prototype.Sprite,
            ),
        ),
        prototype.Billboard(),
        prototype.PhysicsBody(
            body=bullet_body,
            world=world._uid,
        ),
    )


def main():
    ECSShowBase()
    base.disable_mouse()
    base.accept('escape', sys.exit)
    base.cam.set_pos(4, -5, 2)
    base.cam.look_at(0, 0, 0)

    system_types = [
        prototype.ManageModels,
        clock.DetermineTimestep,
        prototype.DeterminePhysicsTimestep,
        prototype.DoPhysics,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    # Bullet world
    bullet_world = BulletWorld()
    bullet_world.set_gravity(Vec3(0, 0, -9.81))

    if debug:
        debugNode = BulletDebugNode('Debug')
        debugNode.showWireframe(True)
        debugNode.showConstraints(True)
        debugNode.showBoundingBoxes(False)
        debugNode.showNormals(False)
        debugNP = render.attachNewNode(debugNode)
        debugNP.show()
        bullet_world.setDebugNode(debugNP.node())

    world = base.ecs_world.create_entity(
        clock.Clock(clock=clock.panda3d_clock),
        prototype.PhysicsWorld(world=bullet_world, timestep=1/30),
    )
    base.ecs_world._flush_component_updates()

    # Something for the models to fall on
    bullet_body = BulletRigidBodyNode()
    bullet_body.set_mass(0.0)
    bullet_body.add_shape(
        BulletBoxShape(Vec3(base_size, base_size, 0.1)),
        TransformState.makePos(Point3(0, 0, 0)),
    )
    bullet_body.add_shape(
        BulletBoxShape(Vec3(base_size, 0.1, wall_height)),
        TransformState.makePos(Point3(0, -base_size, wall_height)),
    )
    bullet_body.add_shape(
        BulletBoxShape(Vec3(base_size, 0.1, wall_height)),
        TransformState.makePos(Point3(0, base_size, wall_height)),
    )
    bullet_body.add_shape(
        BulletBoxShape(Vec3(0.1, base_size, wall_height)),
        TransformState.makePos(Point3(-base_size, 0, wall_height)),
    )
    bullet_body.add_shape(
        BulletBoxShape(Vec3(0.1, base_size, wall_height)),
        TransformState.makePos(Point3(base_size, 0, wall_height)),
    )

    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=prototype.transform(pos=Vec3(0, 0, -1)),
        ),
        prototype.PhysicsBody(
            body=bullet_body,
            world=world._uid,
        ),
    )

    # Regularly add a ball

    def add_ball(task):    
        bullet_body = BulletRigidBodyNode()
        bullet_body.set_linear_sleep_threshold(0)
        bullet_body.set_angular_sleep_threshold(0)
        bullet_body.set_mass(1.0)

        bullet_body.add_shape(BulletSphereShape(ball_size))

        func = random.choice([
            add_smiley,
            add_panda,
            add_mr_man_static,
            add_mr_man_dynamic,
        ])
        func(world, bullet_body)

        return task.again

    base.do_method_later(creation_interval, add_ball, 'add ball')

    # Start
    base.run()


if __name__ == '__main__':
    main()
