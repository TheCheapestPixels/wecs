"""
Simple movement System and component.

The Component holds a 3D vector which represents the direction and speed
of the Entity which uses it.

The System makes sure that on every update() the position of the Entity
(actually, it's model) is updated according to the vector.
"""
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
    """
    The Component holds a 3D vector which represents the vector of the
    Entity which uses it.
    The vector represents is the 3D change that should happen during one second.
    """
    vector: Vec3


class MoveObject(System):
    """
    This System update the position of the Entity's :class:Model according to it's
    movement vector.
    """
    entity_filters = {
        'move': and_filter([
            Model,
            Scene,  # fixme is Scene really necessary?
            Position,
            Movement,
        ]),
    }

    def update(self, entities_by_filter):
        """
        On update, iterate all 'move' entities. For each:
            - Get its position
            - Get its movement(vector)
            - Get its model
            - finally, update its model according to position and vector

        Note the position is update by the vector multiplied by dt, which is
        the deltaTime since the previous update, as the update function is called
         several times per second.

        :param entities_by_filter:
        """
        for entity in entities_by_filter['move']:
            position = entity[Position]
            movement = entity[Movement]
            model = entity[Model]

            position.value += movement.vector * globalClock.dt
            model.node.set_pos(position.value)
