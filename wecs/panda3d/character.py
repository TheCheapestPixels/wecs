from math import sqrt
from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionSphere
from panda3d.core import CollisionCapsule
from panda3d.core import CollisionNode

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .model import Model
from .model import Scene
from .model import Clock


@Component()
class MovementSensors:
    tag_name: str = 'collision_sensors' # FIXME: Symbolify
    solids: dict = field(default_factory=lambda:dict())
    contacts: dict = field(default_factory=lambda:dict())
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    moves: dict = field(default_factory=lambda:dict())
    debug: bool = False


@Component()
class CharacterController:
    heading: float = 0.0
    pitch: float= 0.0
    move_x: float = 0.0
    move_y: float = 0.0
    max_heading: float = 90.0
    max_pitch: float= 90.0
    max_move_x: float = 100.0
    max_move_y: float = 100.0
    translation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    jumps: bool = False


@Component()
class FallingMovement:
    gravity: Vec3 = field(default_factory=lambda:Vec3(0, 0, -9.81))
    inertia: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    local_gravity: Vec3 = field(default_factory=lambda:Vec3(0, 0, -9.81))
    ground_contact: bool = False


@Component()
class JumpingMovement:
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


@Component()
class CollisionSensors:
    tag_name: str = 'collision_sensors' # FIXME: Symbolify
    solids: dict = field(default_factory=lambda:dict())
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    debug: bool = False


#

class CollisionSystem(System):
    def init_sensors(self, sensors, scene, model):
        if sensors.debug:
            sensors.traverser.show_collisions(scene.node)
        
        for tag, solid in sensors.solids.items():
            solid['tag'] = tag
            if solid['shape'] is CollisionSphere:
                self.add_sphere(solid, sensors, model)
            elif solid['shape'] is CollisionCapsule:
                self.add_capsule(solid, sensors, model)

    def add_sphere(self, solid, sensors, model):
        shape = CollisionSphere(solid['center'], solid['radius'])
        node = NodePath(CollisionNode(sensors.tag_name))
        node.node().add_solid(shape)
        node.reparent_to(model.node)
        sensors.traverser.add_collider(node, sensors.queue)
        node.set_python_tag(sensors.tag_name, solid['tag'])
        solid['node'] = node
        if sensors.debug:
            node.show()

    def add_capsule(self, solid, sensors, model):
        shape = CollisionCapsule(
            solid['end_a'],
            solid['end_b'],
            solid['radius'],
        )
        node = NodePath(CollisionNode(sensors.tag_name))
        node.node().add_solid(shape)
        node.reparent_to(model.node)
        sensors.traverser.add_collider(node, sensors.queue)
        node.set_python_tag(sensors.tag_name, solid['tag'])
        solid['node'] = node
        if sensors.debug:
            node.show()

    # def destroy_entity(self, filter_name, entity, component):
    #     if isinstance(component, MoveChecker):
    #         checker = component
    #     else:
    #         checker = entity[MoveChecker]
    #     if isinstance(component, CharacterHull):
    #         hull = component
    #     else:
    #         hull = entity[CharacterHull]
    #     sensors.traverser.remove_collider(hull.node)
    #     hull.solid.destroy()
    #     hull.node.destroy()

    def run_sensors(self, sensors, scene):
        sensors.contacts = {tag: [] for tag in sensors.solids.keys()}
        sensors.traverser.traverse(scene.node)
        sensors.queue.sort_entries()
        for entry in sensors.queue.entries:
            tag = entry.from_node.get_python_tag(sensors.tag_name)
            sensors.contacts[tag].append(entry)


class CheckMovementSensors(CollisionSystem):
    entity_filters = {
        'sensors': and_filter([
            MovementSensors,
            Model,
            Scene,
        ]),
    }

    def init_entity(self, filter_name, entity):
        sensors = entity[MovementSensors]
        scene = entity[Scene]
        model = entity[Model]
        self.init_sensors(sensors, scene, model)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sensors']:
            sensors = entity[MovementSensors]
            scene = entity[Scene]
            self.run_sensors(sensors, scene)


class UpdateCharacter(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            controller = entity[CharacterController]
            model = entity[Model]

            xy_dist = sqrt(controller.move_x**2 + controller.move_y**2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist
            controller.translation = Vec3(
                controller.move_x * controller.max_move_x * xy_scaling * dt,
                controller.move_y * controller.max_move_y * xy_scaling * dt,
                0,
            )
            
            heading_delta = controller.heading * controller.max_heading * dt
            preclamp_pitch = model.node.get_p() + controller.pitch * controller.max_pitch * dt
            clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
            pitch_delta = clamped_pitch - preclamp_pitch
            controller.rotation = Vec3(
                heading_delta,
                pitch_delta,
                0,
            )


class PredictBumping(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            scene = entity[Scene]
            clock = entity[Clock]


class PredictFalling(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            FallingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            scene = entity[Scene]
            clock = entity[Clock]
            falling_movement = entity[FallingMovement]

            falling_movement.local_gravity = model.node.get_relative_vector(
                scene.node,
                falling_movement.gravity,
            )
            frame_gravity = falling_movement.local_gravity * clock.timestep
            falling_movement.inertia += frame_gravity

            sensors = entity[CollisionSensors]
            if 'lifter' in sensors.solids.keys():
                lifter = sensors.solids['lifter']
                node = lifter['node']
                controller = entity[CharacterController]
                frame_inertia = falling_movement.inertia * clock.timestep
                node.set_pos(lifter['center'] + controller.translation + frame_inertia)


class CheckCollisionSensors(CollisionSystem):
    entity_filters = {
        'sensors': and_filter([
            CollisionSensors,
            Model,
            Scene,
        ]),
    }

    def init_entity(self, filter_name, entity):
        sensors = entity[CollisionSensors]
        scene = entity[Scene]
        model = entity[Model]
        self.init_sensors(sensors, scene, model)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sensors']:
            sensors = entity[CollisionSensors]
            scene = entity[Scene]
            self.run_sensors(sensors, scene)


class ExecuteJumping(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            FallingMovement,
            JumpingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            falling_movement = entity[FallingMovement]
            jumping_movement = entity[JumpingMovement]
            if controller.jumps and falling_movement.ground_contact:
                falling_movement.inertia += jumping_movement.impulse


class ExecuteFalling(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            FallingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            sensors = entity[CollisionSensors]
            controller = entity[CharacterController]
            model = entity[Model]
            scene = entity[Scene]
            clock = entity[Clock]
            falling_movement = entity[FallingMovement]
            falling_movement.ground_contact = False
            frame_falling = falling_movement.inertia * clock.timestep

            if len(sensors.contacts['lifter']) > 0:
                lifter = sensors.solids['lifter']['node']
                center = sensors.solids['lifter']['center']
                radius = sensors.solids['lifter']['radius']
                height_corrections = []
                for contact in sensors.contacts['lifter']:
                    if contact.get_surface_normal(lifter).get_z() > 0.0:
                        contact_point = contact.get_surface_point(lifter) - center
                        x = contact_point.get_x()
                        y = contact_point.get_y()
                        # x**2 + y**2 + z**2 = radius**2
                        # z**2 = radius**2 - (x**2 + y**2)
                        expected_z = -sqrt(radius**2 - (x**2 + y**2))
                        actual_z = contact_point.get_z()
                        height_corrections.append(actual_z - expected_z)
                if height_corrections:
                    frame_falling += Vec3(0, 0, max(height_corrections))
                    falling_movement.inertia = Vec3(0, 0, 0)
                    falling_movement.ground_contact = True

            controller.translation += frame_falling


class ExecuteMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            controller = entity[CharacterController]
            model.node.set_pos(model.node, controller.translation)
            model.node.set_hpr(model.node, controller.rotation)
