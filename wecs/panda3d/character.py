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
from wecs.core import or_filter

from .model import Model
from .model import Scene
from .model import Clock

from .camera import ThirdPersonCamera
from .camera import TurntableCamera


@Component()
class FloatingMovement:
    speed: float = 200.0
    turning_speed: float = 60.0


@Component()
class CharacterController:
    # Input or AI
    move: Vec3 = field(default_factory=lambda:Vec3(0,0,0))
    heading: float = 0.0
    pitch: float = 0.0
    jumps: bool = False
    sprints: bool = False
    crouches: bool = False
    # FIXME: Shouldn't be used anymore
    max_heading: float = 90.0
    max_pitch: float = 90.0
    # Intention of movement
    translation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    clamp_pitch: bool = True
    # Speed bookkeeping
    last_translation_speed: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    last_rotation_speed: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))


@Component()
class WalkingMovement:
    speed: float = 10.0
    backwards_multiplier: float = 0.5
    turning_speed: float = 60.0


@Component()
class SprintingMovement:
    speed: float = 20.0


@Component()
class CrouchingMovement:
    speed: float = 1.0
    height: float = 0.4


@Component()
class JumpingMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(1, 1, 0))
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


@Component()
class InertialMovement:
    acceleration: float = 30.0
    rotated_inertia: float = 0.5
    node: NodePath = field(default_factory=lambda:NodePath("Inertia"))
    ignore_z: bool = True


@Component()
class TurningBackToCameraMovement:
    view_axis_alignment: float = 1


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
            Model,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            model = entity[Model]
            dt = entity[Clock].timestep

            # Rotation
            controller.rotation = Vec3(
                controller.heading * dt,
                controller.pitch * dt,
                0,
            )

            # Translation
            # Controllers gamepad etc.) fill a whole rectangle of input
            # space, but characters are limited to a circle. If you're
            # strafing diagonally, you still don't get sqrt(2) speed.
            xy_dist = sqrt(controller.move.x**2 + controller.move.y**2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist
            x = controller.move.x * xy_scaling
            y = controller.move.y * xy_scaling
            controller.translation = Vec3(x * dt, y * dt, 0)


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


class Floating(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            FloatingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            floating = entity[FloatingMovement]

            character.translation *= floating.speed
            character.rotation *= floating.turning_speed


class Walking(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            WalkingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            walking = entity[WalkingMovement]

            speed = walking.speed
            if character.sprints and SprintingMovement in entity:
                speed = entity[SprintingMovement].speed
            if character.crouches and CrouchingMovement in entity:
                speed = entity[CrouchingMovement].speed
            if character.move.y < 0:
                speed *= walking.backwards_multiplier

            character.translation *= speed
            character.rotation *= walking.turning_speed
            character.rotation.y = 0  # No pitch adjustment while walking


class TurningBackToCamera(System):
    entity_filters = {
        'character': and_filter([
            TurningBackToCameraMovement,
            CharacterController,
            Model,
            ThirdPersonCamera,
            TurntableCamera,
            Clock,
            or_filter([
                WalkingMovement,
                FloatingMovement,
            ]),
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            model = entity[Model]
            camera = entity[ThirdPersonCamera]
            turntable = entity[TurntableCamera]
            turning = entity[TurningBackToCameraMovement]
            if WalkingMovement in entity:
                movement = entity[WalkingMovement]
            else:
                movement = entity[FloatingMovement]
            dt = entity[Clock].timestep

            if not (character.move.x == 0 and character.move.y == 0):
                # What's the angle to turn?
                camera_heading = turntable.pivot.get_h() % 360
                if camera_heading > 180.0:
                    camera_heading = camera_heading - 360.0
                # How fast do we have to turn to achieve that?
                rotation_angle = movement.turning_speed * dt
                turning_speed = camera_heading / rotation_angle
                if abs(turning_speed) > 1.0:
                    turning_speed /= abs(turning_speed)
                # And how much does that really influence the behavior?
                turning_speed *= turning.view_axis_alignment
                old_heading = character.heading
                character.heading += turning_speed
                character.heading = max(min(character.heading, 1), -1)
                # Since the camera rotates with the character, we need
                # to counteract that as well. So what angle did we
                # correct turning by?
                delta_heading = character.heading - old_heading
                delta_heading_angle = delta_heading * movement.turning_speed * dt
                # We don't clamp the result. Too fast cameras are not a
                # problem, and this hopefully feels more consistent.
                turntable.heading -= delta_heading_angle / turntable.turning_speed / dt


class Inertiing(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            InertialMovement,
            Model,
            Clock,
        ]),
    }

    def init_entity(self, filter_name, entity):
        movement = entity[InertialMovement]
        model = entity[Model]
        movement.node.reparent_to(model.node)
        movement.node.set_hpr(0, 0, 0)

    def destroy_entity(self, filter_name, entity, components_by_type):
    # detach InertialMovement.node
        import pdb; pdb.set_trace()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            model = entity[Model]
            character = entity[CharacterController]
            inertia = entity[InertialMovement]

            # Usually you want to apply inertia only to x and y, and
            # ignore z, so we cache it.
            old_z = character.translation.z

            # We use inertia.node to represent "last frame's" model
            # orientation, scaled for how much inertia you'd like to
            # keep model-relative. Wow, what a sentence...
            # When you run forward and turn around, where should inertia
            # carry you? Physically, towards your new backward
            # direction. The opposite end of the scale of realism is
            # that your inertia vector turns around with you, and keeps
            # carrying you towards your new forward.
            # So if inertia.rotated_inertia = 1.0, inertia.node will
            # be aligned with the model, and thus the inertia vector
            # turns with you. If inertia.rotated_inertia = 0.0,
            # inertia.node will extrapolate the model's past rotation,
            # and the inertia vector will thus be kept still relative to
            # the surroundings.
            inertia.node.set_hpr(
                -character.last_rotation_speed * dt * (1 - inertia.rotated_inertia),
            )
            last_speed_vector = model.node.get_relative_vector(
                inertia.node,
                character.last_translation_speed,
            )

            # Now we calculate the wanted speed difference, and scale it
            # within gameplay limits.
            wanted_speed_vector = character.translation / dt
            delta_v = wanted_speed_vector - last_speed_vector
            max_delta_v = inertia.acceleration * dt
            if delta_v.length() > max_delta_v:
                capped_delta_v = delta_v / delta_v.length() * max_delta_v
                character.translation = (last_speed_vector + capped_delta_v) * dt

            if inertia.ignore_z:
                character.translation.z = old_z


class Bumping(CollisionSystem):
    entity_filters = {
        'character': and_filter([
            Scene,
            CharacterController,
            BumpingMovement,
            Clock,
            Model,
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
            Model,
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
            Scene,
            Clock,
            Model,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            falling_movement = entity[FallingMovement]
            jumping_movement = entity[JumpingMovement]
            if controller.jumps and falling_movement.ground_contact:
                falling_movement.inertia += jumping_movement.impulse


# Transcribe the final intended movement to the model, making it an
# actual movement.

class ExecuteMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            controller = entity[CharacterController]
            dt = entity[Clock].timestep

            # Translation: Simple self-relative movement for now.
            model.node.set_pos(model.node, controller.translation)
            controller.last_translation_speed = controller.translation / dt

            # Rotation
            if controller.clamp_pitch:
                # Adjust intended pitch until it won't move you over a pole.
                preclamp_pitch = model.node.get_p() + controller.rotation.y
                clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
                controller.rotation.y += clamped_pitch - preclamp_pitch


            model.node.set_hpr(model.node.get_hpr() + controller.rotation)
            controller.last_rotation_speed = controller.rotation / dt
