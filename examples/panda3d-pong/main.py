#!/usr/bin/env python

import sys

from panda3d.core import Vec3
from panda3d.core import Point3
from panda3d.core import VBase3

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.panda3d import ECSShowBase as ShowBase
from wecs import panda3d

import movement
import paddles
import ball


if __name__ == '__main__':
    ShowBase()
    base.disable_mouse()
    base.accept('escape', sys.exit)
    base.cam.set_pos(0, -5, 0)

    system_types = [
        panda3d.LoadModels,
        paddles.ResizePaddles,
        paddles.GivePaddlesMoveCommands,
        movement.MoveObject,
        paddles.PaddleTouchesBoundary,
        ball.BallTouchesBoundary,
        ball.BallTouchesPaddleLine,
        ball.StartBallMotion,
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    # Paddles and ball
    paddle_left = base.ecs_world.create_entity(
        panda3d.Model(model_name='paddle.bam'),
        panda3d.Scene(root=base.aspect2d),
        panda3d.Position(value=Vec3(-1.1, 0, 0)),
        movement.Movement(value=Vec3(0, 0, 0)),
        paddles.Paddle(
            player=0,
            size=0.3,
            speed=0.2,
        ),
    )

    paddle_right = base.ecs_world.create_entity(
        panda3d.Model(model_name='paddle.bam'),
        panda3d.Scene(root=base.aspect2d),
        panda3d.Position(value=Point3(1.1, 0, 0)),
        movement.Movement(value=Vec3(0, 0, 0)),
        paddles.Paddle(
            player=1,
            size=0.3,
            speed=0.2,
        ),
    )

    ball = base.ecs_world.create_entity(
        panda3d.Position(value=Point3(0, 0, 0)),
        panda3d.Model(model_name='ball.bam'),
        panda3d.Scene(root=base.aspect2d),
        ball.Ball(),
        ball.Resting(),
    )

    base.run()
