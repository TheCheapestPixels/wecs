"""
The Paddle Component and System

Each Paddle has information about it's player, size and speed.
"""
from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d import Model
from wecs.panda3d import Scene
from wecs.panda3d import Position

from movement import Movement
from movement import Players


@Component()
class Paddle:
    """
    The Paddle Component holds: an int representing the player controlling it,
    a its speed.
    """

    player: int
    size: float = 0.3


class ResizePaddles(System):
    """
    ResizePaddles ensures that the paddle's size stays updated.
    The idea is that other systems may influence the size by changing
    the paddle's Component state. ResizePaddles will make the actual change
    to the Model.
    """
    entity_filters = {
        'paddle': and_filter([
            Model,
            Paddle,
        ]),
    }

    def update(self, entities_by_filter):
        """
        Update the paddle size by setting the scale of the paddle's Model.
        """
        for entity in entities_by_filter['paddle']:
            model = entity[Model]
            paddle = entity[Paddle]
            model.node.set_scale(paddle.size)


class GivePaddlesMoveCommands(System):
    entity_filters = {
        'paddle': and_filter([
            Model,
            Scene,
            Position,
            Movement,
            Paddle,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['paddle']:
            paddle = entity[Paddle]
            movement = entity[Movement]

            # What keys does the player use?
            if paddle.player == Players.LEFT:
                up_key = KeyboardButton.ascii_key(b'w')
                down_key = KeyboardButton.ascii_key(b's')
            elif paddle.player == Players.RIGHT:
                up_key = KeyboardButton.up()
                down_key = KeyboardButton.down()

            # Read player input
            delta = 0
            if base.mouseWatcherNode.is_button_down(up_key):
                delta += 1
            if base.mouseWatcherNode.is_button_down(down_key):
                delta -= 1

            # Store movement
            movement.direction.z = delta


class PaddleTouchesBoundary(System):
    entity_filters = {
        'paddles': and_filter([
            Model,
            Scene,
            Position,
            Paddle,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in set(entities_by_filter['paddles']):
            model = entity[Model]
            position = entity[Position]
            paddle = entity[Paddle]

            z = position.value.z
            size = paddle.size

            if z + size > 1:
                position.value.z = 1 - size
            elif (z - size) < -1:
                position.value.z = -1 + size
            model.node.set_z(position.value.z)
