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
from paddles import Paddle


@Component()
class Ball:
    pass


@Component()
class Resting:
    pass


class BallTouchesBoundary(System):
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
            np = entity.get_component(Model).node
            z = np.get_z()
            if z > 0.9:
                np.set_z(0.9 - (z - 0.9))
                movement = entity.get_component(Movement).value
                movement.z = -movement.z
            if z < -0.9:
                np.set_z(-0.9 - (z + 0.9))
                movement = entity.get_component(Movement).value
                movement.z = -movement.z


class BallTouchesPaddleLine(System):
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
        paddle_entities = sorted(
            entities_by_filter['paddles'],
            key=lambda e: e.get_component(Paddle).player,
        )
        for entity in set(entities_by_filter['ball']):
            pos = entity.get_component(Position)
            if pos.value.x < -1:
                paddle = paddle_entities[0]
                paddle_z = paddle.get_component(Position).value.z
                paddle_size = paddle.get_component(Paddle).size
                if abs(paddle_z - pos.value.z) > paddle_size:
                    print("SCORE RIGHT!")
                    entity.remove_component(Movement)
                    entity.add_component(Resting())
                    entity.get_component(Position).value = Point3(0, 0, 0)
                else:
                    entity.get_component(Movement).value.x *= -1
                    dist_to_center = paddle_z - pos.value.z
                    normalized_dist = dist_to_center / (paddle_size)
                    movement = entity.get_component(Movement).value
                    speed = abs(movement.x)
                    movement.z -= normalized_dist * speed
            if pos.value.x > 1:
                paddle = paddle_entities[1]
                paddle_z = paddle.get_component(Position).value.z
                paddle_size = paddle.get_component(Paddle).size
                if abs(paddle_z - pos.value.z) > paddle_size:
                    print("SCORE LEFT!")
                    entity.remove_component(Movement)
                    entity.add_component(Resting())
                    entity.get_component(Position).value = Point3(0, 0, 0)
                else:
                    entity.get_component(Movement).value.x *= -1
                    dist_to_center = paddle_z - pos.value.z
                    normalized_dist = dist_to_center / paddle_size
                    movement = entity.get_component(Movement).value
                    speed = abs(movement.x)
                    movement.z -= normalized_dist * speed


class StartBallMotion(System):
    entity_filters = {
        'ball': and_filter([
            Model,
            Scene,
            Position,
            Resting,
            Ball,
        ]),
    }

    def update(self, entities_by_filter):
        start_balls = base.mouseWatcherNode.is_button_down(
            KeyboardButton.space(),
        )
        if start_balls:
            for entity in set(entities_by_filter['ball']):
                entity.remove_component(Resting)
                entity.add_component(Movement(value=Vec3(-1, 0, 0)))
