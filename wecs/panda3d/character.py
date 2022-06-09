"""
The character controller mechanic is a collection of game-typical modes
of movement, steered by user input or AI, applied to a node that
represents the character.

The core of the mechanic consists of the :class:`CharacterController`
(which in the following will be abbreviated as `character`) component,
and the systems :class:`UpdateCharacter` and :class:`ExecuteMovement`. 
Additionally, :class:`Clock` and :class:`Input` see heavy use. Together,
these implement a basic character that can be moved around.

* UpdateCharacter
  * If the entity has an `Input` component, and
    `UpdateCharacter.input_context` (default: 'character_movement') is
    in `Input.contexts`, then that context is read from the device
    listener and transcribed to the `CharacterController` component.
    Specifically:
    * `character.move` (`x` and `y`) is set to the context's `direction`
    * `character.heading` is set to the negative of the context's
      `rotation.x`
    * `character.pitch` is set to the context's `rotation.y`
    * Some boolean flags (FIXME: ...which should probably be moved to
      their respective movement mechanics) are set:
      * `character.jumps` to the context's `jump`
      * `character.sprints` to the context's `sprint`
      * `character.crouches` to the context's `crouch`
    
    So far, these values are in "input space", using a value range of
    [-1; 1]. Also, so far they only represent the *intention* to make a
    movement, and no actual movement will happen in this system.

    If no `Input` component is present, or the system's input context is
    not handled by that component, then the fields listed above are not
    changed. It falls to the developer to set them some other way (e.g.
    by an AI system), otherwise the character will keep moving based on
    the last used input (which may be the values set at the
    `CharacterController` component's creation).
  * Time scaling is applied to these values, meaning that they are
    understood as being "requested movement per second", and are scaled
    down to the movement requested for just this frame.
    * `character.rotation` is a time-scaled `Vec3` HPR version of
      `character.heading` and `character.pitch`.
    * `character.translation` is a `Vec3` XYZ version of
      `character.move`. Additionally, since the input values are based
      on a square, should they be outside of the unit circle, they are
      scaled down to be on the edge of it, in the same direction as the
      input was using.
* ExecuteMovement: The values which so far were only intentions are now
  applied to the node.
  * The node is moved (`set_pos`) relative to itself by
    `character.translate`.
  * The node's rotation is adjusted by adding `character.rotation`.
    Before that, if `character.clamp_pitch` is True,
    `character.rotation.y` is adjusted so that the node's pitch will
    stay in the [-89.99; 89.99] range. 
  * `character.last_rotation_speed` and
    `character.last_translation_speed` are set to un-timescaled versions
    of the applied movement and rotation.

Obviously, this alone does us not get us very far; But now we can add
further mechanics between `UpdateCharacter` and `ExecuteMovement`. They
can change the values on the `CharacterController` to make it conform
with the level geometry, other entities present on it, and the physics
and mechanics of the game world. In many cases, they consist simply of
a component type that indicates that a character is subject to a certain
movement type's rules (and with which parameters, e.g. maximum speed),
and the system to process it (and the `CharacterController`).

Provided in this module are:

* Floating: Scales the character's intentions up by the speed-per-second
  values on the `FloatingMovement` component.
* Walking: Scales the intentions by the speed in `WalkingMovement`,
  `SprintingMovement`, or `CrouchingMovement` (where applicable), and
  sets the pitch adjustment to 0.
* Inertiing: Applies corrections to the intention to account for
  inertia, making the character "want" to continue their movement the
  same way as the frame before.
* Bumping: Checks whether the movement as calculated so far will cause
  a collision with surrounding terrain / characters, and change the
  intended movement to where Panda3D's CollisionPusher would move the
  charactter.
* Falling: Applies gravity, then lifts the node back up based on
  collisions with the ground.
* Jumping: Adds an upward impulse to the `FallingMovement`, so that the
  character will "fall upwards" starting the next frame.
* TurningBackToCamera: Makes the character turn towards the direction
  into which the camera looks, away from the camera itself.
"""

from math import sqrt
from math import copysign
from math import asin
from math import pi
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
from wecs.core import Proxy
from wecs.core import ProxyType
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.mechanics.clock import Clock
from wecs.panda3d.input import Input

from wecs.panda3d.prototype import Model
from wecs.panda3d.prototype import Geometry

from .camera import Camera
from .camera import ObjectCentricCameraMode

from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import FALLING_MASK


@Component()
class CharacterController:
    """
    A moving entity.

    :param Vec3 move: (0, 0, 0) - speed of relative movement
    :param float heading: 0.0 - horizontal direction the character is headed
    :param float pitch: 0.0 - vertical direction the character is headed
    :param bool jumps: False - Triggers a jump
    :param bool sprints: False - Is True when sprinting
    :param bool crouches: False - Is True when crouching

    Remaining variables are calculated by systems.
    """

    # Input or AI
    move: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    heading: float = 0.0
    pitch: float = 0.0
    jumps: bool = False
    sprints: bool = False
    crouches: bool = False
    # FIXME: Shouldn't be used anymore
    max_heading: float = 90.0
    max_pitch: float = 90.0
    # Intention of movement
    translation: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    clamp_pitch: bool = True
    # Speed bookkeeping
    last_translation_speed: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    last_rotation_speed: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    # Gravity vector
    gravity: Vec3 = field(default_factory=lambda: Vec3(0, 0, -1))


@Component()
class CameraReorientedInput:
    node: NodePath = field(default_factory=lambda: NodePath('reorient'))


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
    speed: Vec3 = field(default_factory=lambda: Vec3(1, 1, 0))
    impulse: bool = field(default_factory=lambda: Vec3(0, 0, 5))


@Component()
class InertialMovement:
    '''
    This character can jump.

    :param float acceleration: 30.0 - rate at which to accumulate speed
    :param float rotated_inertia: 0.5 - how much rotation impacts inertia
    :param NodePath node: NodePath("Inertia") - relative position based on inertia
    :param bool ignore_z: True - ignore_z
    :param bool delta_inputs: False - Inputs in the character indicate a wish for change in speed, not absolute speed
    '''
    acceleration: float = 30.0
    rotated_inertia: float = 0.5
    node: NodePath = field(default_factory=lambda: NodePath("Inertia"))
    ignore_z: bool = True
    delta_inputs: bool = False


@Component()
class AutomaticTurningMovement:
    '''
    This character can be given a direction towards which to orient,
    which will be used in addition or instead of that coming from
    character input.

    Examples are making the character face along the camera's view axis,
    turning towards the direction in which they are moving, facing
    towards a direction that the player is indicating, or staying locked
    onto a target.

    :param Vec3 direction: Direction in model space to turn towards
    :param float alignment: 1.0 - turning rate
    :param float angle:
    '''
    direction: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    alignment: float = 1.0
    angle: float = 0.0


@Component()
class TurningBackToCameraMovement:
    '''
    This character has a tendency to face away from the camera.

    :param float view_axis_alignment: 1 - rate at which to turn away
    :param float threshold: Minimum linear speed at which to turn.
    '''
    view_axis_alignment: float = 1.0
    threshold: float = 0.2


@Component()
class TwinStickMovement:
    pass


@Component()
class FacingMovement:
    pass


@Component()
class BumpingMovement:
    '''
    This character's horizontal movement is hindered by collisions.
    '''
    tag_name: str = 'bumping'
    from_collide_mask: int = BUMPING_MASK
    into_collide_mask: int = BUMPING_MASK
    # The name of the node to use if `solids` is None
    node_name: str = 'bumper'
    solids: dict = None  # field(default_factory=lambda: dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerPusher)
    debug: bool = False


@Component()
class FallingMovement:
    '''
    This character falls unless on solid ground.
    '''
    inertia: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    ground_contact: bool = False
    tag_name: str = 'falling'
    from_collide_mask: int = FALLING_MASK
    into_collide_mask: int = 0x0
    node_name: str = 'lifter'
    solids: dict = field(default_factory=lambda: dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerQueue)
    debug: bool = False


@Component()
class FrictionalMovement:
    '''
    A slow-down is applied to the character.
    '''
    half_life: float = 5.0


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
            Proxy('character_node'),  # Not used, but required for a complete character
            Clock,
            CharacterController,
        ]),
        'input': and_filter([
            CharacterController,
            Input,
        ]),
    }
    proxies = {'character_node': ProxyType(Model, 'node')}
    input_context = 'character_movement'

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                character = entity[CharacterController]

                if context['direction'] is not None:
                    character.move.x = context['direction'].x
                    character.move.y = context['direction'].y
                else:
                    character.move = Vec2(0, 0)
                if context['rotation'] is not None:
                    character.heading = -context['rotation'].x
                    character.pitch = context['rotation'].y
                else:
                    character.heading = 0
                    character.pitch = 0

                # Special movement modes.
                # By default, you run ("sprint"), unless you press e, in
                # which case you walk. You can crouch by pressing q; this
                # overrides walking and running. Jump by pressing space.
                # This logic is implemented by the Walking system. Here,
                # only intention is signalled.
                character.jumps = False
                character.sprints = False
                character.crouches = False

                if 'jump' in context:
                    character.jumps = context['jump']
                if 'sprint' in context:
                    character.sprints = context['sprint']
                if 'crouch' in context:
                    character.crouches = context['crouch']

        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
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
            xy_dist = sqrt(controller.move.x ** 2 + controller.move.y ** 2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist
            x = controller.move.x * xy_scaling
            y = controller.move.y * xy_scaling
            z = controller.move.z * xy_scaling
            controller.translation = Vec3(x * dt, y * dt, z * dt)


class ReorientInputBasedOnCamera(System):
    """
    By default, player input is relative to the character. If it is
    viewed from a third person perspective, it is usually preferable to
    rotate them so that they align with the camera instead.
    """
    entity_filters = {
        'reorient': and_filter([
            Camera,
            ObjectCentricCameraMode,
            CameraReorientedInput,
            Proxy('model'),
            CharacterController,
        ]),
    }
    proxies = {
        'model': ProxyType(Model, 'node'),
    }

    def enter_filter_reorient(self, entity):
        camera = entity[Camera]
        reorienter = entity[CameraReorientedInput]

        reorienter.node.reparent_to(camera.camera)

    def exit_filter_reorient(self, entity):
        reorienter = entity[CameraReorientedInput]

        reorienter.node.detach_node()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['reorient']:
            model_proxy = self.proxies['model']
            model = entity[model_proxy.component_type]
            model_node = model_proxy.field(entity)
            character = entity[CharacterController]
            camera = entity[Camera]
            reorienter = entity[CameraReorientedInput]

            reorienter.node.set_p(model_node, 0)
            character.translation = model_node.get_relative_vector(
                reorienter.node,
                character.translation,
            )


# Movement systems
#
# These systems modify the intended movement as stored on the
# character controller to conform to external constraints. A
# recurring element is that systems will run a collision
# traverser, so first we provide a helpful base class.

class CollisionSystem(System):
    proxies = {
        'character_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def init_sensors(self, entity, movement):
        solids = movement.solids
        for tag, solid in solids.items():
            if 'shape' in solid:  # Create solids from specification
                solid['tag'] = tag
                if solid['shape'] is CollisionSphere:
                    shape = CollisionSphere(solid['center'], solid['radius'])
                elif solid['shape'] is CollisionCapsule:
                    shape = CollisionCapsule(
                        solid['end_a'],
                        solid['end_b'],
                        solid['radius'],
                    )
                else:
                    raise Exception("Shape unsupported.")
                self.add_shape(entity, movement, solid, shape)
            else:  # Fetch solids from model
                model_node = self.proxies['character_node'].field(entity)
                solid_nodes = model_node.find_all_matches(
                    f'**/{movement.node_name}',
                )
                # FIXME: This is a temporary prevention of sing multiple
                # solids in one movement system. This whole .py needs to
                # be refactored to account for multiple ones.
                assert len(solids) == 1
                solid_node = solid_nodes[0]

                solid_node.reparent_to(model_node)

                solid['node'] = solid_node
                solid_objects = solid_node.node().get_solids()
                # FIXME: As above, please refactor this .py to account
                # for multiple solids.
                assert len(solids) == 1
                solid_object = solid_objects[0]
                solid['shape'] = solid_object.type
                if solid['shape'] == CollisionSphere:
                    solid['center'] = solid_object.center
                    solid['radius'] = solid_object.radius

                # FIXME: This is mostly copypasta from add_solid, which
                # should be broken up.
                node = solid_node.node()
                node.set_from_collide_mask(movement.from_collide_mask)
                node.set_into_collide_mask(movement.into_collide_mask)
                movement.traverser.add_collider(
                    solid_node,
                    movement.queue,
                )
                node.set_python_tag(movement.tag_name, movement)
                if movement.debug:
                    solid_node.show()

        if movement.debug:
            scene_proxy = self.proxies['scene_node']
            scene = entity[scene_proxy.component_type]
            scene_node = scene_proxy.field(entity)

            movement.traverser.show_collisions(scene_node)

    def add_shape(self, entity, movement, solid, shape):
        model_proxy = self.proxies['character_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)

        node = NodePath(
            CollisionNode(
                f'{movement.tag_name}-{solid["tag"]}',
            ),
        )
        solid['node'] = node
        node.node().add_solid(shape)
        node.node().set_from_collide_mask(movement.from_collide_mask)
        node.node().set_into_collide_mask(movement.into_collide_mask)
        node.reparent_to(model_node)
        movement.traverser.add_collider(node, movement.queue)
        node.set_python_tag(movement.tag_name, movement)
        if 'debug' in solid and solid['debug']:
            node.show()

    def run_sensors(self, entity, movement):
        scene_proxy = self.proxies['scene_node']
        scene = entity[scene_proxy.component_type]
        scene_node = scene_proxy.field(entity)

        movement.traverser.traverse(scene_node)
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
        Sets ´AutomaticTurningMovement.direction´ parallel to the 
        camera's view axis.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.character.AutomaticTurningMovement`
            | :class:`wecs.panda3d.character.TurningBackToCameraMovement`
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.WalkingMovement` or :class:`wecs.panda3d.character.FloatingMovement`
o            | :class:`wecs.panda3d.camera.Camera`
            | :class:`wecs.panda3d.camera.ObjectCentricCamera`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('character_node'),
            Clock,
            AutomaticTurningMovement,
            TurningBackToCameraMovement,
            CharacterController,
            or_filter([
                WalkingMovement,
                FloatingMovement,
            ]),
            Camera,
            ObjectCentricCameraMode,
        ])
    }
    proxies = {'character_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            camera = entity[Camera]
            center = entity[ObjectCentricCameraMode]
            turning = entity[TurningBackToCameraMovement]
            autoturning = entity[AutomaticTurningMovement]
            model_node = self.proxies['character_node'].field(entity)

            dt = entity[Clock].game_time

            autoturning.direction = model_node.get_relative_vector(
                camera.pivot,
                Vec3(0, 1, 0),
            )
            if character.move.xy.length() >= turning.threshold * dt:
                autoturning.alignment = turning.view_axis_alignment
            else:
                autoturning.alignment = 0.0


class DirectlyIndicateDirection(System):
    entity_filters = {
        'character': and_filter([
            Proxy('model'),
            AutomaticTurningMovement,
            TwinStickMovement,
            CharacterController,
            Camera,
            ObjectCentricCameraMode,
        ])
    }
    proxies = {'model': ProxyType(Model, 'node')}
    input_context = 'character_direction'

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                self.process_input(context, entity)

    def process_input(self, context, entity):
        model_proxy = self.proxies['model']
        model_node = model_proxy.field(entity)
        camera = entity[Camera]
        turning = entity[AutomaticTurningMovement]

        if context['direction'] is not None:
            turning.direction = model_node.get_relative_vector(
                camera.pivot,
                Vec3(
                    context['direction'].x,
                    context['direction'].y,
                    0,
                ),
            )
        else:
            turning.direction = Vec3(0, 1, 0)


class AutomaticallyTurnTowardsDirection(System):
    '''
        Turns character towards ´AutomaticTurningMovement.direction´ 
        (and the camera in the opposite direction, so the net result is
        no camera movement in scene space).

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.character.AutomaticTurningMovement`
            | :class:`wecs.panda3d.character.CharacterController`
            | :class:`wecs.panda3d.character.WalkingMovement` or :class:`wecs.panda3d.character.FloatingMovement`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('character_node'),
            Clock,
            AutomaticTurningMovement,
            CharacterController,
            or_filter([
                WalkingMovement,
                FloatingMovement,
            ]),
        ])
    }
    proxies = {'character_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            turning = entity[AutomaticTurningMovement]
            model_node = self.proxies['character_node'].field(entity)
            if WalkingMovement in entity:
                movement = entity[WalkingMovement]
            else:
                movement = entity[FloatingMovement]
            dt = entity[Clock].game_time

            if turning.direction.xy.length() > 0.0:
                # How much would he have to adjust heading to face
                # towards the given vector?
                direc = Vec2(turning.direction.xy)
                angle = Vec2(0, 1).signed_angle_deg(direc)
                
                # How far can we turn this frame? Clamp to that.
                max_angle = movement.turning_speed
                if abs(angle) > max_angle:
                    angle = copysign(max_angle, angle)
                # How much of that do we *want* to turn?
                angle *= turning.alignment

                # So let's turn, and clamp, in case we're already turning.
                old_rotation = character.rotation.x
                character.rotation.x += angle
                character.rotation.x = min(
                    character.rotation.x,
                    max_angle,
                )
                character.rotation.x = max(
                    character.rotation.x,
                    -max_angle,
                )
                # Since the camera rotates with the character, we need
                # to counteract that as well.
                delta_rotation = character.rotation.x - old_rotation
                turning.angle = delta_rotation

                # FIXME: This needs to be its own system
                camera = entity[Camera]
                camera.pivot.set_h(camera.pivot.get_h() - delta_rotation)


class FaceMovement(System):
    '''
        Orient the model along the velocity vector projected onto the
        x/y plane; Model points to where it moves, but stays upright.

        Components used
            | :class:`wecs.panda3d.character.FacingMovement`
            | :class:`wecs.panda3d.prototype.Geometry`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.character.CharacterController`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('geometry_node'),
            Clock,
            CharacterController,
            FacingMovement,
        ]),
    }
    proxies = {'geometry_node': ProxyType(Geometry, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            geometry_proxy = self.proxies['geometry_node']
            geometry = entity[geometry_proxy.component_type]
            geometry_node = geometry_proxy.field(entity)

            controller = entity[CharacterController]
            x, y, z = controller.last_translation_speed
            geometry_node.look_at(x, y, 0)


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
            Proxy('character_node'),
            Clock,
            CharacterController,
            InertialMovement,
        ]),
    }
    proxies = {'character_node': ProxyType(Model, 'node')}

    def enter_filter_character(self, entity):
        movement = entity[InertialMovement]
        model_proxy = self.proxies['character_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)

        movement.node.reparent_to(model_node)
        movement.node.set_hpr(0, 0, 0)

    def exit_filter_character(self, entity):
        # detach InertialMovement.node
        import pdb;
        pdb.set_trace()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].game_time
            model_proxy = self.proxies['character_node']
            model = entity[model_proxy.component_type]
            model_node = model_proxy.field(entity)
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
            # the surroundings. And if it is between those, it will
            # interpolate accordingly.
            inertia.node.set_hpr(
                -character.last_rotation_speed * dt * (1 - inertia.rotated_inertia),
            )
            last_speed_vector = model_node.get_relative_vector(
                inertia.node,
                character.last_translation_speed,
            )

            # Now we calculate the wanted speed difference, and scale it
            # within gameplay limits.
            wanted_speed_vector = character.translation / dt
            if inertia.delta_inputs:
                delta_v = wanted_speed_vector
            else:
                delta_v = wanted_speed_vector - last_speed_vector
            max_delta_v = inertia.acceleration * dt
            if delta_v.length() > max_delta_v:
                capped_delta_v = delta_v / delta_v.length() * max_delta_v
            else:
                capped_delta_v = delta_v

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
            Proxy('scene_node'),
            Proxy('character_node'),
            Clock,
            CharacterController,
            BumpingMovement,
        ]),
    }
    proxies = {
        'character_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def enter_filter_character(self, entity):
        movement = entity[BumpingMovement]
        self.init_sensors(entity, movement)
        bumper = movement.solids[movement.tag_name]
        node = bumper['node']
        movement.queue.add_collider(node, node)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            scene_proxy = self.proxies['scene_node']
            scene = entity[scene_proxy.component_type]
            scene_node = scene_proxy.field(entity)
            character = entity[CharacterController]
            movement = entity[BumpingMovement]
            bumper = movement.solids[movement.tag_name]
            node = bumper['node']
            node.set_pos(character.translation)
            movement.traverser.traverse(scene_node)
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
            Proxy('scene_node'),
            Proxy('character_node'),
            Clock,
            CharacterController,
            FallingMovement,
        ]),
    }
    proxies = {
        'character_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
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
        character = entity[CharacterController]
        model_proxy = self.proxies['character_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)
        scene_proxy = self.proxies['scene_node']
        scene = entity[scene_proxy.component_type]
        scene_node = scene_proxy.field(entity)

        clock = entity[Clock]
        controller = entity[CharacterController]
        falling_movement = entity[FallingMovement]

        # Adjust inertia by gravity
        frame_gravity = character.gravity * clock.game_time
        falling_movement.inertia += frame_gravity

        # Adjust lifter collider by inertia
        frame_inertia = falling_movement.inertia * clock.game_time
        lifter = falling_movement.solids['lifter']
        node = lifter['node']

        node.set_pos(controller.translation + frame_inertia)

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
                # FIXME: We're assuming a sphere here.
                # We only use the lower half of the sphere, no equator.
                if contact.get_surface_normal(lifter).get_z() > 0.0:
                    contact_point = contact.get_surface_point(lifter)
                    contact_point -= center  # In solid's space
                    xy = contact_point.xy
                    expected_z = -sqrt(radius ** 2 - xy.length() ** 2)
                    actual_z = contact_point.get_z()
                    height_corrections.append(actual_z - expected_z)
            if height_corrections:
                frame_falling += Vec3(0, 0, max(height_corrections))
                falling_movement.inertia = Vec3(0, 0, 0)
                falling_movement.ground_contact = True

        # Now we know how falling / lifting influences the movement
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
            Proxy('scene_node'),
            Proxy('character_node'),
            Clock,
            CharacterController,
            JumpingMovement,
            FallingMovement,
        ]),
    }
    proxies = {
        'character_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            controller = entity[CharacterController]
            falling_movement = entity[FallingMovement]
            jumping_movement = entity[JumpingMovement]
            if controller.jumps and falling_movement.ground_contact:
                falling_movement.inertia += jumping_movement.impulse


class Frictioning(System):
    '''
    Applies a slow-down to the character.
    '''
    entity_filters = {
        'character': and_filter([
            Clock,
            CharacterController,
            FrictionalMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].game_time
            character = entity[CharacterController]
            friction = entity[FrictionalMovement]

            character.translation *= 0.5 ** (dt / friction.half_life)


class WalkSpeedLimiting(System):
    '''
    Applies a slow-down to the character.
    '''
    entity_filters = {
        'character': and_filter([
            Clock,
            CharacterController,
            WalkingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].game_time
            character = entity[CharacterController]
            walking = entity[WalkingMovement]

            v_length = character.translation.length()
            if v_length > walking.speed * dt:
                character.translation.normalize()
                character.translation *= walking.speed * dt


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
            Proxy('character_node'),
            Clock,
            CharacterController,
        ]),
    }
    proxies = {'character_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model_proxy = self.proxies['character_node']
            model = entity[model_proxy.component_type]
            character = entity[CharacterController]
            dt = entity[Clock].game_time

            # Translation: Simple self-relative movement for now.
            model_node = model_proxy.field(entity)
            model_node.set_pos(model_node, character.translation)
            character.last_translation_speed = character.translation / dt

            # Rotation
            if character.clamp_pitch:
                # Adjust intended pitch until it won't move you over a pole.
                preclamp_pitch = model_node.get_p() + character.rotation.y
                clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
                character.rotation.y += clamped_pitch - preclamp_pitch

            model_node.set_hpr(model_node, character.rotation)
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
            Clock,
            CharacterController,
            Stamina,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            stamina = entity[Stamina]
            dt = entity[Clock].timestep
            av = abs(character.move.x) + abs(character.move.y)
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
