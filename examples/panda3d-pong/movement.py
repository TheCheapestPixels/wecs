from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d import Position
from wecs.panda3d import Model
from wecs.panda3d import Scene


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
            pos = entity.get_component(Position)
            move = entity.get_component(Movement)
            node = entity.get_component(Model).node
            pos.value += move.value * globalClock.dt
            node.set_pos(pos.value)
