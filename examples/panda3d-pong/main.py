#!/usr/bin/env python

import sys

from panda3d.core import Vec3, Point3, VBase3

from wecs.core import World, Component, System
from wecs.panda3d import ECSShowBase as ShowBase

import systems
import components


if __name__ == '__main__':
    ShowBase()
    base.disable_mouse()
    base.accept('escape', sys.exit)
    base.cam.set_pos(0, -5, 0)

    system_types = [
        systems.LoadModels,
        systems.ResizePaddles,
        systems.GivePaddlesMoveCommands,
        systems.MoveObject,
        systems.PaddleTouchesBoundary,
        systems.BallTouchesBoundary,
        systems.BallTouchesPaddleLine,
        systems.StartBallMotion,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    # Paddles and ball
    paddle_left = base.ecs_world.create_entity()
    paddle_left.add_component(components.Position(value=Vec3(-1.1, 0, 0)))
    paddle_left.add_component(components.Movement(value=Vec3(0, 0, 0)))
    paddle_left.add_component(components.Model(
        model_name='paddle.bam',
    ))
    paddle_left.add_component(components.Scene(root=base.aspect2d))
    paddle_left.add_component(components.Paddle(player=0, size=0.3, speed=0.2))

    paddle_right = base.ecs_world.create_entity()
    paddle_right.add_component(components.Position(value=Point3(1.1, 0, 0)))
    paddle_right.add_component(components.Movement(value=Vec3(0, 0, 0)))
    paddle_right.add_component(components.Model(
        model_name='paddle.bam',
    ))
    paddle_right.add_component(components.Scene(root=base.aspect2d))
    paddle_right.add_component(components.Paddle(
        player=1,
        size=0.3,
        speed=0.2,
    ))

    ball = base.ecs_world.create_entity()
    ball.add_component(components.Position(value=Point3(0, 0, 0)))
    ball.add_component(components.Model(
        model_name='ball.bam',
    ))
    ball.add_component(components.Scene(root=base.aspect2d))
    ball.add_component(components.Ball())
    ball.add_component(components.Resting())

    base.run()
