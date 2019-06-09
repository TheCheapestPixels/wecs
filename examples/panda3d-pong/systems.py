from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import KeyboardButton

from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter

from components import Paddle
from components import Ball
from components import Resting
from components import Position
from components import Movement
from components import Model
from components import Scene


class LoadModels(System):
    entity_filters = {
        'model': and_filter([Model, Position, Scene]),
    }

    def init_entity(self, filter_name, entity):
        # Load
        model_c = entity.get_component(Model)
        model_node = base.loader.load_model(model_c.model_name)

        # Add to scene under a new
        scene_root = entity.get_component(Scene).root
        model_root = scene_root.attach_new_node("model_component_root")
        model_node.reparent_to(model_root)
        model_c.node = model_root

        model_node.set_pos(model_c.position)
        model_node.set_hpr(model_c.rotation)
        model_node.set_scale(model_c.scale)

    def destroy_entity(self, filter_name, entity, component):
        # Remove from scene
        # FIXME: ...and the root node that init_entity created
        if isinstance(component, Model):
            component.node.destroy_node()
        else:
            entity.get_component(Model).node.destroy_node()


class GivePaddlesMoveCommands(System):
    entity_filters = {
        'paddle':and_filter([
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
                if abs(paddle_z - pos.value.z) > paddle_size / 2:
                    print("SCORE RIGHT!")
                    entity.remove_component(Movement)
                    entity.add_component(Resting())
                    entity.get_component(Position).value = Point3(0, 0, 0)
                else:
                    entity.get_component(Movement).value.x *= -1
                    dist_to_center = paddle_z - pos.value.z
                    normalized_dist = dist_to_center / (paddle_size / 2)
                    movement = entity.get_component(Movement).value
                    speed = abs(movement.x)
                    movement.z -= normalized_dist * speed
            if pos.value.x > 1:
                paddle = paddle_entities[1]
                paddle_z = paddle.get_component(Position).value.z
                paddle_size = paddle.get_component(Paddle).size
                if abs(paddle_z - pos.value.z) > paddle_size / 2:
                    print("SCORE LEFT!")
                    entity.remove_component(Movement)
                    entity.add_component(Resting())
                    entity.get_component(Position).value = Point3(0, 0, 0)
                else:
                    entity.get_component(Movement).value.x *= -1
                    dist_to_center = paddle_z - pos.value.z
                    normalized_dist = dist_to_center / (paddle_size / 2)
                    movement = entity.get_component(Movement).value
                    speed = abs(movement.x)
                    movement.z -= normalized_dist * speed


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
            if pos.z + size / 2 > 1:
                pos.z = 1 - size / 2
                np = entity.get_component(Model).node
                np.set_z(pos.z)
            if pos.z - size / 2 < -1:
                pos.z = -1 + size / 2
                np = entity.get_component(Model).node
                np.set_z(pos.z)


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
