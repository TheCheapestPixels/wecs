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
from wecs.panda3d.input import Input

from .model import Model
from .model import Geometry
from .model import Scene
from .model import Clock

from .camera import Camera
from .camera import ObjectCentricCameraMode


@Component()
class CharacterController:
    '''
    A moving entity.

    :param Vec3 move: (0, 0, 0) - speed of relative movement
    :param float heading: 0.0 - horizontal direction the character is headed
    :param float pitch: 0.0 - vertical direction the character is headed
    :param bool jumps: False - Triggers a jump
    :param bool sprints: False - Is True when sprinting
    :param bool crouches: False - Is True when crouching

    Remaining variables are calculated by systems.
    '''

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
class FloatingMovement:
    '''
    This character floats, moves with 6 degrees of freedom.

    :param float speed: 200.0 - speed of relative forward movement
    :param float turning_speed: 60.0 - rotation speed
    '''
    speed: float = 200.0
    turning_speed: float = 60.0


@Component()
class WalkingMovement:
    '''
    This character walks, moves on the horizontal dimensions.

    :param float speed: 10.0 - speed of relative forward movement
    :param float backwards_multiplier: 0.5 - how much faster is backwards movement
    :param float turning_speed: 60.0 - rotation speed
    '''
    speed: float = 10.0
    backwards_multiplier: float = 0.5
    turning_speed: float = 60.0


@Component()
class SprintingMovement:
    '''
    This character can sprint.

    :param float speed: 20.0 - speed of relative forward movement when sprinting
    '''
    speed: float = 20.0


@Component()
class CrouchingMovement:
    '''
    This character can crouch.

    :param float speed: 10.0 - speed of relative forward movement when crouching
    :param float height: 0.4 - the height of the character when crouched
    '''
    speed: float = 10.0
    height: float = 0.4


@Component()
class JumpingMovement:
    '''
    This character can jump.

    :param Vec3 speed: (1, 1, 0) - speed of relative movement when jumping
    :param float impulse: (0, 0, 5) - initial speed of jump
    '''
    speed: Vec3 = field(default_factory=lambda:Vec3(1, 1, 0))
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


@Component()
class InertialMovement:
    '''
    This character can jump.

    :param float acceleration: 30.0 - rate at which to accumulate speed
    :param float rotated_inertia: 0.5 - how much rotation impacts inertia
    :param NodePath node: NodePath("Inertia") - relative position based on inertia
    :param bool ignore_z: True - ignore_z
    '''
    acceleration: float = 30.0
    rotated_inertia: float = 0.5
    node: NodePath = field(default_factory=lambda:NodePath("Inertia"))
    ignore_z: bool = True


@Component()
class TurningBackToCameraMovement:
    '''
    This character has a tendency to face away from the camera.

    :param float view_axis_alignment: 1 - rate at which to turn away
    '''
    view_axis_alignment: float = 1
    threshold: float = 0.2


@Component()
class FacingMovement:
    pass


@Component()
class BumpingMovement:
    '''
    This character's horizontal movement is hindered by collisions.
    '''
    tag_name: str = 'bumping'
    solids: dict = field(default_factory=lambda:dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerPusher)
    debug: bool = False


@Component()
class FallingMovement:
    '''
    This character falls unless on solid ground.
    '''
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
    '''
    Convert input to character movement.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.mode.Model`
    '''
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Clock,
            Model,
        ]),
        'input': and_filter([
            CharacterController,
            Input,
        ]),
    }
    input_context = 'character_movement'

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                character = entity[CharacterController]

                character.move.x = context['direction'].x
                character.move.y = context['direction'].y
                character.heading = -context['rotation'].x
                character.pitch = context['rotation'].y

                # Special movement modes.
                # By default, you run ("sprint"), unless you press e, in
                # which case you walk. You can crouch by pressing q; this
                # overrides walking and running. Jump by pressing space.
                # This logic is implemented by the Walking system. Here,
                # only intention is signalled.
                character.jumps = context['jump']
                character.sprints = context['sprint']
                character.crouches = context['crouch']

        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            model = entity[Model]
            dt = entity[Clock].game_time

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
            z = controller.move.z * xy_scaling
            controller.translation = Vec3(x * dt, y * dt, z * dt)

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
    '''
        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.FloatingMovement`
    '''
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
    '''
        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.WalkingMovement`
    '''
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
    '''
        Turns character away from the camera.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.TurningBackToCameraMovement`
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.camera.ThirdPersonCamera`
            | :class:`wecs.panda3d.camera.TurntableCamera`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'character': and_filter([
            TurningBackToCameraMovement,
            CharacterController,
            Model,
            Camera,
            ObjectCentricCameraMode,
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
            camera = entity[Camera]
            center = entity[ObjectCentricCameraMode]
            turning = entity[TurningBackToCameraMovement]
            if WalkingMovement in entity:
                movement = entity[WalkingMovement]
            else:
                movement = entity[FloatingMovement]
            dt = entity[Clock].game_time

            if character.move.x ** 2 + character.move.y**2 > (turning.threshold * dt) ** 2:
                # What's the angle to turn?
                target_angle = camera.pivot.get_h() % 360
                if target_angle > 180.0:
                    target_angle = target_angle - 360.0
                # How far can we turn this frame? Clamp to that.
                max_angle = movement.turning_speed * dt
                if abs(target_angle) > max_angle:
                    target_angle *= max_angle / abs(target_angle)
                # How much of that do we *want* to turn?
                target_angle *= turning.view_axis_alignment

                # So let's turn, and clamp, in case we're already turning.
                old_rotation = character.rotation.x
                character.rotation.x += target_angle
                character.rotation.x = min(character.rotation.x, movement.turning_speed * dt)
                character.rotation.x = max(character.rotation.x, -movement.turning_speed * dt)
                # Since the camera rotates with the character, we need
                # to counteract that as well.
                delta_rotation = character.rotation.x - old_rotation
                camera.pivot.set_h(camera.pivot.get_h() - delta_rotation)


class FaceMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Geometry,
            Clock,
            FacingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            geometry = entity[Geometry]
            controller = entity[CharacterController]
            x,y,z = controller.last_translation_speed
            geometry.node.look_at(x, y, 0)


class Inertiing(System):
    '''
        Accelerate character, as opposed to an instantanious velocity.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.InertialMovement`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.model.clock`
    '''
    entity_filters = {
        'character': and_filter([
            CharacterController,
            InertialMovement,
            Model,
            Clock,
        ]),
    }

    def enter_filter_character(self, entity):
        movement = entity[InertialMovement]
        model = entity[Model]
        movement.node.reparent_to(model.node)
        movement.node.set_hpr(0, 0, 0)

    def exit_filter_character(self, entity):
    # detach InertialMovement.node
        import pdb; pdb.set_trace()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].game_time
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
    '''
        Stop the character from moving through solid geometry.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.model.Scene`
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.BumpingMovement`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.model.Model`
    '''
    entity_filters = {
        'character': and_filter([
            Scene,
            CharacterController,
            BumpingMovement,
            Clock,
            Model,
        ]),
    }

    def enter_filter_character(self, entity):
        movement = entity[BumpingMovement]
        self.init_sensors(entity, movement)
        bumper = movement.solids['bumper']
        node = bumper['node']
        movement.queue.add_collider(node, node)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            scene = entity[Scene]
            character = entity[CharacterController]
            movement = entity[BumpingMovement]
            bumper = movement.solids['bumper']
            node = bumper['node']
            node.set_pos(character.translation)
            movement.traverser.traverse(scene.node)
            character.translation = node.get_pos()


class Falling(CollisionSystem):
    '''
        Stop the character from falling through solid geometry.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.FallingMovement`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.model.Model`
    '''
    entity_filters = {
        'character': and_filter([
            CharacterController,
            FallingMovement,
            Scene,
            Clock,
            Model,
        ]),
    }

    def enter_filter_character(self, entity):
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
        frame_gravity = falling_movement.local_gravity * clock.game_time
        falling_movement.inertia += frame_gravity

        # Adjust lifter collider by inertia
        frame_inertia = falling_movement.inertia * clock.game_time
        lifter = falling_movement.solids['lifter']
        node = lifter['node']
        node.set_pos(lifter['center'] + controller.translation + frame_inertia)

    def fall_and_land(self, entity):
        falling_movement = entity[FallingMovement]
        clock = entity[Clock]
        controller = entity[CharacterController]

        falling_movement.ground_contact = False
        frame_falling = falling_movement.inertia * clock.game_time
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
    '''
        Make the character jump.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.JumpingMovement`
            | :class:`wecs.panda3d.character.FallingMovement`
            | :class:`wecs.panda3d.model.Scene`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.model.Model`
    '''
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
    '''
    Transcribe the final intended movement to the model, making it an actual movement.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.model.Clock`
    '''
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
            character = entity[CharacterController]
            dt = entity[Clock].game_time

            # Translation: Simple self-relative movement for now.
            model.node.set_pos(model.node, character.translation)
            character.last_translation_speed = character.translation / dt

            # Rotation
            if character.clamp_pitch:
                # Adjust intended pitch until it won't move you over a pole.
                preclamp_pitch = model.node.get_p() + character.rotation.y
                clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
                character.rotation.y += clamped_pitch - preclamp_pitch


            model.node.set_hpr(model.node.get_hpr() + character.rotation)
            character.last_rotation_speed = character.rotation / dt


### Stamina

@Component()
class Stamina:
    '''
    This character's movement abilities are determined by stamina.

    :param float current: 100 - stamina currently left
    :param float maximum: 100 - maximum amount of stamina
    :param float recovery: 100 - rate of recovery (at all times)
    :param float crouch_drain: 10 - cost of crouching
    :param float move_drain: 10 - cost of walking
    :param float sprint_drain: 10 - cost of sprinting (on top of walking)
    :param float jump_drain: 20 - cost of a single jump
    '''

    current: float = 100.0
    maximum: float = 100.0
    recovery: float = 10
    crouch_drain: float = 10
    move_drain: float = 10
    sprint_drain: float = 10
    jump_drain: float = 20


class UpdateStamina(System):
    '''
    Disable or allow character's movement abilities based on stamina.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.Stamina`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Stamina,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            stamina = entity[Stamina]
            dt = entity[Clock].timestep
            av = abs(character.move.x)+abs(character.move.y)
            drain = 0
            if character.move.x or character.move.y:
                drain = stamina.move_drain * av
            if character.sprints and SprintingMovement in entity:
                if stamina.current > stamina.sprint_drain * av:
                    drain = stamina.sprint_drain * av
                else:
                    character.sprints = False
            elif character.crouches and CrouchingMovement in entity:
                if stamina.current > stamina.crouch_drain * av:
                    drain = stamina.crouch_drain * av
                else:
                    character.crouches = False
            if character.jumps and JumpingMovement in entity:
                if stamina.current > stamina.jump_drain * av:
                    drain += stamina.jump_drain
                else:
                    character.jumps = False
            stamina.current -= drain * dt
            stamina.current += stamina.recovery * dt
            stamina.current = clamp(stamina.current, 0, stamina.maximum)
