from panda3d.core import KeyboardButton
from panda3d.core import Vec3
from panda3d.core import Point3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d import Model
from wecs.panda3d import Scene
from wecs.panda3d import Position

from movement import Movement
from movement import Players
from paddles import Paddle


@Component()
class Ball:
    pass


@Component()
class Resting:
    pass


class BallTouchesBoundary(System):
    """
    BallTouchesBoundary ensures the balls is bounced of the top and bottom
    of the court.
    """
    entity_filters = {
        'ball': and_filter([
            Model,
            Scene,
            Position,
            Movement,
            Ball,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['ball']:
            model = entity[Model]
            movement = entity[Movement]

            # The ball's size is assumed to be 0.1, and if it moved over
            # the upper or lower boundary (1 / -1), we reflect it.
            z = model.node.get_z()
            if z > 0.9:
                model.node.set_z(0.9 - (z - 0.9))
                movement.direction.z = -movement.direction.z
            if z < -0.9:
                model.node.set_z(-0.9 - (z + 0.9))
                movement.direction.z = -movement.direction.z


class BallTouchesPaddleLine(System):
    """
    BallTouchesPaddleLine takes care what happens when the ball
    reaches the line of one of the paddles:
    Either the paddle is in reach, and the ball reflects off it,
    or the other player has scored, and the game is reset to its
    starting state.
    """
    entity_filters = {
        'ball': and_filter([
            Model,
            Scene,
            Position,
            Movement,
            Ball,
        ]),
        'paddles': and_filter([
            Model,
            Scene,
            Position,
            Paddle,
        ]),
    }

    def update(self, entities_by_filter):
        """
        The Update goes over all the relevant Entities (which should be only the ball)
        and check whether it reached each paddle's line. A ball always has a Position component
        so it has so we can check it's x position. Same goes for the paddles.
        If x is touching the paddle's line , we check whether the ball hit the paddle or not.
        If it hit the paddle it would bounce back.
        If it misses the paddle, it would print "SCORE" and stop the balls movement.
        Note that to stop the ball's movement the update deletes the Movement component from the
        ball's Entity. It also adds the Resting component to ensure that the StartBallMotion
        System will return the ball to a moving state when the game restarts.
        """
        paddles = {
            p[Paddle].player: p for p in entities_by_filter['paddles']
        }

        for entity in set(entities_by_filter['ball']):
            position = entity[Position]
            movement = entity[Movement]

            # Whose line are we behind, if any?
            if position.value.x < -1:
                player = Players.LEFT
            elif position.value.x > 1:
                player = Players.RIGHT
            else:
                continue

            paddle = paddles[player]
            paddle_position = paddle[Position]
            paddle_paddle = paddle[Paddle]

            paddle_z = paddle_position.value.z
            paddle_size = paddle_paddle.size

            if abs(paddle_z - position.value.z) > paddle_size:
                # The paddle is too far away, a point is scored.
                print("SCORE!")
                del entity[Movement]
                entity[Resting] = Resting()
                position.value = Point3(0, 0, 0)
            else:
                # Reverse left-right direction
                movement.direction.x *= -1
                # Adjust up-down speed based on where the paddle was hit
                dist_to_center = paddle_z - position.value.z
                normalized_dist = dist_to_center / (paddle_size)
                speed = abs(movement.direction.x)
                movement.direction.z -= normalized_dist * speed


class StartBallMotion(System):
    """
    StartBallMotion ensures that the game restarts after the start key is pressed.
    """
    entity_filters = {
        'ball': and_filter([
            Model,
            Scene,
            Position,
            Resting,
            Ball,
        ]),
    }
    start_key = KeyboardButton.space()

    def update(self, entities_by_filter):
        """
        Check whether the resting ball should be started?
        Note that restarting the ball's movement means removing the Entity's
        Resting Component, and adding it's Movement component with the desired
        direction.
        """

        start_key_is_pressed = base.mouseWatcherNode.is_button_down(StartBallMotion.start_key)

        if start_key_is_pressed:
            for entity in set(entities_by_filter['ball']):
                del entity[Resting]
                entity[Movement] = Movement(direction=Vec3(-1, 0, 0))
