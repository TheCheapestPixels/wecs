from math import sqrt
from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionHandlerPusher
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
class BumpingMovement:
    tag_name: str = 'bumping'
    solids: dict = field(default_factory=lambda:dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerPusher)
    debug: bool = False


@Component()
class FallingMovement:
    gravity: Vec3 = field(default_factory=lambda:Vec3(0, 0, -9.81))
    inertia: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    local_gravity: Vec3 = field(default_factory=lambda:Vec3(0, 0, -9.81))
    ground_contact: bool = False
    tag_name: str = 'falling'
    solids: dict = field(default_factory=lambda:dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerQueue)
    debug: bool = False


@Component()
class JumpingMovement:
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


#

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


# Movements

class CollisionSystem(System):
    def init_sensors(self, entity, movement):
        solids = movement.solids
        for tag, solid in solids.items():
            solid['tag'] = tag
            if solid['shape'] is CollisionSphere:
                shape = CollisionSphere(solid['center'], solid['radius'])
                self.add_shape(entity, movement, solid, shape)
            elif solid['shape'] is CollisionCapsule:
                shape = CollisionCapsule(
                    solid['end_a'],
                    solid['end_b'],
                    solid['radius'],
                )
                self.add_shape(entity, movement, solid, shape)
        if movement.debug:
            movement.traverser.show_collisions(entity[Scene].node)
            

    def add_shape(self, entity, movement, solid, shape):
        model = entity[Model]
        node = NodePath(CollisionNode(
            '{}-{}'.format(
                movement.tag_name,
                solid['tag'],
            )
        ))
        solid['node'] = node
        node.node().add_solid(shape)
        node.node().set_into_collide_mask(0)
        node.reparent_to(model.node)
        movement.traverser.add_collider(node, movement.queue)
        node.set_python_tag(movement.tag_name, movement)
        if 'debug' in solid and solid['debug']:
            node.show()

    def run_sensors(self, entity, movement):
        scene = entity[Scene]

        movement.traverser.traverse(scene.node)
        movement.queue.sort_entries()
        movement.contacts = movement.queue.entries


class Bumping(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            Scene,
            Model,
            CharacterController,
            BumpingMovement,
            Clock,
        ]),
    }

    def init_entity(self, filter_name, entity):
        movement = entity[BumpingMovement]
        self.init_sensors(entity, movement)
        bumper = movement.solids['bumper']
        node = bumper['node']
        movement.queue.add_collider(node, node)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            scene = entity[Scene]
            controller = entity[CharacterController]
            movement = entity[BumpingMovement]
            bumper = movement.solids['bumper']
            node = bumper['node']
            node.set_pos(controller.translation)
            movement.traverser.traverse(scene.node)
            controller.translation = node.get_pos()


# class Bumping(CollisionSystem):
#     entity_filters = {
#         'character': and_filter([
#             CharacterController,
#             BumpingMovement,
#             Model,
#             Scene,
#             Clock,
#         ]),
#     }
# 
#     def init_entity(self, filter_name, entity):
#         self.init_sensors(entity, entity[BumpingMovement])
# 
#     def update(self, entities_by_filter):
#         for entity in entities_by_filter['character']:
#             self.predict_movement(entity)
#             self.run_sensors(entity, entity[BumpingMovement])
#             self.adjust(entity)
# 
#     def predict_movement(self, entity):
#         controller = entity[CharacterController]
#         movement = entity[BumpingMovement]
#         bumper = movement.solids['bumper']
#         node = bumper['node']
#         node.set_pos(controller.translation)
# 
#     def adjust(self, entity):
#         controller = entity[CharacterController]
#         movement = entity[BumpingMovement]
#         adjustment = Vec3(0, 0, 0)
#         for contact in movement.contacts:
#             interior = contact.get_interior_point(contact.from_node_path)
#             surface = contact.get_surface_point(contact.from_node_path)
#             back_vector = interior - surface
#             adjustment += Vec3(back_vector.x, back_vector.y, 0)
#         if len(movement.contacts) > 0:
#              adjustment /= len(movement.contacts)
#         controller.translation += adjustment


class Falling(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            FallingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }
        
    def init_entity(self, filter_name, entity):
        self.init_sensors(entity, entity[FallingMovement])

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            # Adjust the falling inertia by gravity, and position the
            # lifter collider.
            self.predict_falling(entity)
            # Find collisions with the ground. 
            self.run_sensors(entity, entity[FallingMovement])
            # Adjust the character's intended translation so that his
            # falling is stoppedby the ground.
            self.fall_and_land(entity)

    def predict_falling(self, entity):
        model = entity[Model]
        scene = entity[Scene]
        clock = entity[Clock]
        controller = entity[CharacterController]
        falling_movement = entity[FallingMovement]

        # Adjust inertia by gravity
        falling_movement.local_gravity = model.node.get_relative_vector(
            scene.node,
            falling_movement.gravity,
        )
        frame_gravity = falling_movement.local_gravity * clock.timestep
        falling_movement.inertia += frame_gravity

        # Adjust lifter collider by inertia
        frame_inertia = falling_movement.inertia * clock.timestep
        lifter = falling_movement.solids['lifter']
        node = lifter['node']
        node.set_pos(lifter['center'] + controller.translation + frame_inertia)

    def fall_and_land(self, entity):
        falling_movement = entity[FallingMovement]
        clock = entity[Clock]
        controller = entity[CharacterController]

        falling_movement.ground_contact = False
        frame_falling = falling_movement.inertia * clock.timestep
        if len(falling_movement.contacts) > 0:
            lifter = falling_movement.solids['lifter']['node']
            center = falling_movement.solids['lifter']['center']
            radius = falling_movement.solids['lifter']['radius']
            height_corrections = []
            for contact in falling_movement.contacts:
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

        # Now we know how falling / lifting influences the character move
        controller.translation += frame_falling


class Jumping(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            JumpingMovement,
            FallingMovement,
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
