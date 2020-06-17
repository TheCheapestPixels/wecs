from panda3d.core import Vec3
from panda3d.core import Point3

from wecs import panda3d

# These modules contain the actual game mechanics, which we are tying
# together into an application in this file:

import movement
import paddles
import ball


system_types = [
    # Attach the entity's Model. This gives an entity a node as
    # presence in the scene graph.
    panda3d.SetupModels,
    # Attach Geometry to the Model's node.
    panda3d.ManageGeometry,
    # If the Paddle's size has changed, apply it to the Model.
    paddles.ResizePaddles,
    # Read player input and store it on Movement
    paddles.GivePaddlesMoveCommands,
    # Apply the Movement
    movement.MoveObject,
    # Did the paddle move too far? Back to the boundary with it!
    paddles.PaddleTouchesBoundary,
    # If the Ball has hit the edge, it reflects off it.
    ball.BallTouchesBoundary,
    # If the ball is on a player's paddle's line, two things can
    # happen:
    # * The paddle is in reach, and the ball reflects off it.
    # * The other player has scored, and the game is reset to its
    #   starting state.
    ball.BallTouchesPaddleLine,
    # If the ball is in its Resting state, and the players indicate
    # that the game should start, the ball is set in motion.
    ball.StartBallMotion,
]


paddle_left = base.ecs_world.create_entity(
    panda3d.Model(),
    panda3d.Geometry(file='paddle.bam'),
    panda3d.Scene(node=base.aspect2d),
    panda3d.Position(value=Vec3(-1.1, 0, 0)),
    movement.Movement(direction=Vec3(0, 0, 0)),
    paddles.Paddle(player=paddles.Players.LEFT),
)

paddle_right = base.ecs_world.create_entity(
    panda3d.Model(),
    panda3d.Geometry(file='paddle.bam'),
    panda3d.Scene(node=base.aspect2d),
    panda3d.Position(value=Point3(1.1, 0, 0)),
    movement.Movement(direction=Vec3(0, 0, 0)),
    paddles.Paddle(player=paddles.Players.RIGHT),
)

ball = base.ecs_world.create_entity(
    panda3d.Position(value=Point3(0, 0, 0)),
    panda3d.Model(),
    panda3d.Geometry(file='ball.bam'),
    panda3d.Scene(node=base.aspect2d),
    ball.Ball(),
    ball.Resting(),
)
