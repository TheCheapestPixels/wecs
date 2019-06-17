from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d import Model
from wecs.panda3d import Scene
from wecs.panda3d import Position

from movement import Movement


@Component()
class Paddle:
    player: int
    size: float
    speed: float


class ResizePaddles(System):
    entity_filters = {
        'paddle': and_filter([
            Model,
            Paddle,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['paddle']:
            model = entity.get_component(Model).node
            size = entity.get_component(Paddle).size
            model.set_scale(size)


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
        left = 0
        if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key(b'w')):
            left += 1
        if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key(b's')):
            left -= 1

        right = 0
        if base.mouseWatcherNode.is_button_down(KeyboardButton.up()):
            right += 1
        if base.mouseWatcherNode.is_button_down(KeyboardButton.down()):
            right -= 1

        for entity in entities_by_filter['paddle']:
            if entity.get_component(Paddle).player == 0:
                entity.get_component(Movement).value.z = left
            elif entity.get_component(Paddle).player == 1:
                entity.get_component(Movement).value.z = right


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
            pos = entity.get_component(Position).value
            size = entity.get_component(Paddle).size
            if pos.z + size  > 1:
                pos.z = 1 - size
                np = entity.get_component(Model).node
                np.set_z(pos.z)
            if (pos.z - size) < -1:
                pos.z = -1 + size
                np = entity.get_component(Model).node
                np.set_z(pos.z)
