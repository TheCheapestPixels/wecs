from math import sqrt
from dataclasses import field

from panda3d.core import Vec2, Vec3
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

from .camera import FirstPersonCamera
from .camera import ThirdPersonCamera


def clamp(i, floor, ceiling):
    return min(ceiling, max(floor, i))


@Component()
class CharacterController:
    node: NodePath = field(default_factory=NodePath)
    heading: float = 0.0
    pitch: float = 0.0
    max_heading: float = 90.0
    max_pitch: float = 90.0
    move: Vec3 = field(default_factory=lambda:Vec3(0,0,0))
    max_move: Vec3 = field(default_factory=lambda:Vec3(20,20,0))
    translation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    jumps: bool = False
    sprints: bool = False
    crouches: bool = False
    runs: bool = False
    walks: bool = False


@Component()
class WalkingMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(20,20,20))
    backwards_multiplier: float = 1.0
    run_threshold: float = 0.5


@Component()
class SprintingMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(30,30,30))


@Component()
class CrouchingMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(5,5,5))
    height: float = 0.4


@Component()
class JumpingMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(1,1,0))
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


@Component()
class AirMovement:
    air_friction: float = 10.0


@Component()
class AcceleratingMovement:
    accelerate: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    slide: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    brake: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    speed: Vec2 = field(default_factory=lambda:Vec2(0, 0))


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


# @Component()
# class MovementSensors:
#     solids: dict = field(default_factory=lambda:dict())
#     contacts: dict = field(default_factory=lambda:dict())
#     traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
#     queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
#     debug: bool = False


class UpdateCharacter(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Clock,
        ]),
    }

    def init_entity(self, filter_name, entity):
        entity[CharacterController].node.reparentTo(render)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            controller = entity[CharacterController]
            # Accelerating movement
            if AcceleratingMovement in entity:
                move = entity[AcceleratingMovement]
                for a, speed in enumerate(move.speed):
                    moving = controller.move[a]
                    max_move = controller.max_move[a]
                    air_friction = 1
                    if AirMovement in entity and FallingMovement in entity:
                        if not entity[FallingMovement].ground_contact:
                            max_move = 9999999
                            air_friction = entity[AirMovement].air_friction
                    step = 0
                    if moving:
                        if speed < max_move*moving:
                            step = move.accelerate[a]/air_friction
                            if speed < 0:
                                step = move.brake[a]/air_friction
                        elif speed > max_move*moving:
                            step = -move.accelerate[a]/air_friction
                            if speed > 0:
                                step = -move.brake[a]/air_friction
                    else:
                        if air_friction == 1:
                            slide = move.slide[a]
                            if speed > slide:
                                step = -slide
                            elif speed < -slide:
                                step = slide
                            else:
                                move.speed[a] = 0
                    move.speed[a] += step
                x = move.speed.x
                y = move.speed.y
            # Normal (linear) movement
            else:
                x = controller.move.x * controller.max_move.x
                y = controller.move.y * controller.max_move.y

            xy_dist = sqrt(controller.move.x**2 + controller.move.y**2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist
            controller.translation = Vec3(x * xy_scaling * dt, y * xy_scaling * dt, 0)

            heading_delta = controller.heading * controller.max_heading * dt
            preclamp_pitch = controller.node.get_p() + controller.pitch * controller.max_pitch * dt
            clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
            pitch_delta = clamped_pitch - preclamp_pitch
            controller.rotation = Vec3(
                heading_delta,
                pitch_delta,
                0,
            )


class HeadingFromCamera(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
            Clock,
            ThirdPersonCamera
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            model = entity[Model]
            clock = entity[Clock]
            camera = entity[ThirdPersonCamera]
            camera_heading = camera.pivot.get_h(render)
            controller_heading = controller.node.get_h()
            if not (controller.move.x == 0 and controller.move.y == 0):
                model.node.set_h(camera_heading)

            rotation_speed = 1
            if AcceleratingMovement in entity:
                speed = entity[AcceleratingMovement].speed
                total = speed[0] + speed[1]
                if total:
                    # Where can I find the highest possible max_move to replace 200 with?
                    rotation_speed -= total/200
            if AirMovement in entity and FallingMovement in entity:
                if not entity[FallingMovement].ground_contact:
                    rotation_speed /= entity[AirMovement].air_friction/5

            angle = (controller_heading - camera_heading)%360
            if angle < 180-rotation_speed:
                controller.heading = -rotation_speed
            if angle > 180+rotation_speed:
                controller.heading = rotation_speed


# Movement systems
#
# These systems modify the intended movement as stored on the
# character controller to conform to external constraints. A
# recurring element is that systems will run a collision
# traverser, so first we provide a helpful base class.

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
        node = NodePath(CollisionNode(
            '{}-{}'.format(
                movement.tag_name,
                solid['tag'],
            )
        ))
        solid['node'] = node
        node.node().add_solid(shape)
        node.node().set_into_collide_mask(0)
        node.reparent_to(entity[CharacterController].node)
        movement.traverser.add_collider(node, movement.queue)
        node.set_python_tag(movement.tag_name, movement)
        if 'debug' in solid and solid['debug']:
            node.show()

    def run_sensors(self, entity, movement):
        scene = entity[Scene]
        movement.traverser.traverse(scene.node)
        movement.queue.sort_entries()
        movement.contacts = movement.queue.entries


class WalkSpeeds(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character   = entity[CharacterController]
            if SprintingMovement in entity and character.sprints:
                character.max_move = entity[SprintingMovement].speed
            elif CrouchingMovement in entity and character.crouches:
                character.max_move = entity[CrouchingMovement].speed
            elif WalkingMovement in entity:
                if character.move.y < 0:
                    multiplier = entity[WalkingMovement].backwards_multiplier
                else:
                    multiplier = 1
                character.max_move = entity[WalkingMovement].speed * multiplier
            if JumpingMovement in entity  and character.jumps:
                character.max_move = entity[JumpingMovement].speed


class Bumping(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            Scene,
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


class Falling(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            FallingMovement,
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
        scene = entity[Scene]
        clock = entity[Clock]
        controller = entity[CharacterController]
        falling_movement = entity[FallingMovement]

        # Adjust inertia by gravity
        falling_movement.local_gravity = controller.node.get_relative_vector(
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


# Transcribe the final intended movement to the character, making it an
# actual movement.

class ExecuteMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            controller.node.set_hpr(controller.node, controller.rotation)
            controller.node.set_pos(controller.node, controller.translation)
            if Model in entity:
                entity[Model].node.set_pos(controller.node.get_pos())
            if ThirdPersonCamera in entity:
                cam = entity[ThirdPersonCamera]
                cam.pivot.set_pos(controller.node.get_pos())
                cam.pivot.set_z(controller.node.get_z()+cam.pivot_height)
