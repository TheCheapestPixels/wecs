from enum import Enum

from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d import Position
from wecs.panda3d import Model
from wecs.panda3d import Scene


class Players(Enum):
    LEFT = 0
    RIGHT = 1


@Component()
class Movement:
    value: Vec3


class MoveObject(System):
    entity_filters = {
        'move': and_filter([
            Model,
            Scene,
            Position,
            Movement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['move']:
            position = entity[Position]
            movement = entity[Movement]
            model = entity[Model]

            position.value += movement.value * globalClock.dt
            model.node.set_pos(position.value)
