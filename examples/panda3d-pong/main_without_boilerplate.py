#!/usr/bin/env python

import sys
import logging

from panda3d.core import Vec3
from panda3d.core import Point3

import wecs
from wecs.core import ProxyType
from wecs.panda3d import ECSShowBase

# These modules contain the actual game mechanics, which we are tying
# together into an application in this file:

import movement
import paddles
import ball


logging.getLogger().setLevel(logging.DEBUG)


if __name__ == '__main__':
    ECSShowBase()  # ShowBase + base.ecs_world + base.add_system()
    base.disable_mouse()
    base.accept('escape', sys.exit)

    model_proxies = {
        'model': ProxyType(wecs.panda3d.prototype.Model, 'node'),
    }
    systems = [
        # Attach the entity's Model. This gives an entity a node as
        # presence in the scene graph.
        # Attach Geometry to the Model's node.
        wecs.panda3d.prototype.ManageModels(),
        # If the Paddle's size has changed, apply it to the Model.
        paddles.ResizePaddles(proxies=model_proxies),
        # Read player input and store it on Movement
        paddles.GivePaddlesMoveCommands(proxies=model_proxies),
        # Apply the Movement
        movement.MoveObject(proxies=model_proxies),
        # Did the paddle move too far? Back to the boundary with it!
        paddles.PaddleTouchesBoundary(),
        # If the Ball has hit the edge, it reflects off it.
        ball.BallTouchesBoundary(proxies=model_proxies),
        # If the ball is on a player's paddle's line, two things can
        # happen:
        # * The paddle is in reach, and the ball reflects off it.
        # * The other player has scored, and the game is reset to its
        #   starting state.
        ball.BallTouchesPaddleLine(),
        # If the ball is in its Resting state, and the players indicate
        # that the game should start, the ball is set in motion.
        ball.StartBallMotion(),
    ]

    # base.add_system(system) adds the system to the world *and* creates
    # a task that will trigger updates. This is how WECS integrates into
    # Panda3D's task manager.
    for sort, system in enumerate(systems):
        base.add_system(system, sort)

    # All systems are set up now, so all that's missing are the
    # entities.

    # left paddle
    base.ecs_world.create_entity(
        wecs.panda3d.prototype.Model(
            parent=base.aspect2d,
            post_attach=wecs.panda3d.prototype.transform(
                pos=Vec3(-1.1, 0, 0),
            ),
        ),
        wecs.panda3d.prototype.Geometry(file='resources/paddle.bam'),
        movement.Movement(direction=Vec3(0, 0, 0)),
        paddles.Paddle(player=paddles.Players.LEFT),
    )

    # right paddle
    base.ecs_world.create_entity(
        wecs.panda3d.prototype.Model(
            parent=base.aspect2d,
            post_attach=wecs.panda3d.prototype.transform(
                pos=Vec3(1.1, 0, 0),
            ),
        ),
        wecs.panda3d.prototype.Geometry(file='resources/paddle.bam'),
        movement.Movement(direction=Vec3(0, 0, 0)),
        paddles.Paddle(player=paddles.Players.RIGHT),
    )

    # ball
    base.ecs_world.create_entity(
        wecs.panda3d.prototype.Model(parent=base.aspect2d),
        wecs.panda3d.prototype.Geometry(file='resources/ball.bam'),
        ball.Ball(),
        ball.Resting(),
    )

    base.run()
