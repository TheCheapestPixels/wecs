"""
Simple movement System and component.

The Component holds a 3D direction which represents the direction and speed
of the Entity which uses it.

The System makes sure that on every update() the position of the component
is updated according to its direction.
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
    The Movement Component holds a 3D vector which represents the direction of the
    component which uses it, for example, the model of the ball, or the paddles.
    It's the 3D change that should happen during one second,so it serves as a "speed"
    element as well.
    """
    direction: Vec3


class MoveObject(System):
    """
    MoveObject update the position of the Entity's :class:Model according to it's
    movement direction.
    """
    entity_filters = {
        'movable': and_filter([
            Model,
            Position,
            Movement,
        ]),
    }

    def update(self, entities_by_filter):
        """
        On update, iterate all 'movable' entities. For each:
            - Get its position
            - Get its movement(direction)
            - Get its model
            - finally, update its model according to position and direction

        Note the position is update by the direction multiplied by dt, which is
        the deltaTime since the previous update, as the update function is called
         several times per second.

        :param entities_by_filter:
        """
        for entity in entities_by_filter['movable']:
            position = entity[Position]
            movement = entity[Movement]
            model = entity[Model]

            position.value += movement.direction * globalClock.dt
            model.node.set_pos(position.value)
