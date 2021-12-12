"""
The character controller mechanic is a collection of game-typical modes
of movement, steered by user input or AI, applied to a node that
represents the character.

The core of the mechanic consists of the :class:`Mover`
(which in the following will be abbreviated as `character`) component,
and the systems :class:`UpdateCharacter` and :class:`ExecuteMovement`. 
Additionally, :class:`Clock` and :class:`Input` see heavy use. Together,
these implement a basic character that can be moved around.

* UpdateCharacter
  * If the entity has an `Input` component, and
    `UpdateCharacter.input_context` (default: 'character_movement') is
    in `Input.contexts`, then that context is read from the device
    listener and transcribed to the `Mover` component.
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
    `Mover` component's creation).
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
can change the values on the `Mover` to make it conform
with the level geometry, other entities present on it, and the physics
and mechanics of the game world. In many cases, they consist simply of
a component type that indicates that a character is subject to a certain
movement type's rules (and with which parameters, e.g. maximum speed),
and the system to process it (and the `Mover`).

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
from wecs.panda3d.prototype import Mover

from .camera import Camera
from .camera import ObjectCentricCameraMode

from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import FALLING_MASK


@Component()
class CharacterController:
    :param bool jumps: False - Triggers a jump
    :param bool sprints: False - Is True when sprinting
    :param bool crouches: False - Is True when crouching
    jumps: bool = False
    sprints: bool = False
    crouches: bool = False


@Component()
class CameraReorientedInput:
    node: NodePath = field(default_factory=lambda: NodePath('reorient'))


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
class WalkingMovement:
    '''
    This mover 'walks', moves on the horizontal dimensions.

    :param float speed: 10.0 - speed of relative forward movement
    :param float backwards_multiplier: 0.5 - how much faster is backwards movement
    :param float turning_speed: 60.0 - rotation speed
    '''
    speed: float = 10.0
    backwards_multiplier: float = 0.5
    turning_speed: float = 60.0


class Walking(System):
    '''
        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.mover.Mover`
            | :class:`wecs.panda3d.mover.WalkingMovement`
    '''
    entity_filters = {
        'mover': and_filter([
            Mover,
            WalkingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            mover = entity[Mover]
            walking = entity[WalkingMovement]

            speed = walking.speed
            if mover.sprints and SprintingMovement in entity:
                speed = entity[SprintingMovement].speed
            if mover.crouches and CrouchingMovement in entity:
                speed = entity[CrouchingMovement].speed
            if mover.move.y < 0:
                speed *= walking.backwards_multiplier

            mover.translation *= speed
            mover.rotation *= walking.turning_speed
            mover.rotation.y = 0  # No pitch adjustment while walking


class UpdateCharacter(System):
    '''
    Convert input to character movement.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.movement.Mover`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.mode.Model`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('character_node'),  # Not used, but required for a complete character
            Clock,
            CharacterController,
            Mover,
        ]),
        'input': and_filter([
            Mover,
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
                mover = entity[Mover]
                if context['direction'] is not None:
                    mover.move.x = context['direction'].x
                    mover.move.y = context['direction'].y
                else:
                    mover.move = Vec2(0, 0)
                if context['rotation'] is not None:
                    mover.heading = -context['rotation'].x
                    mover.pitch = context['rotation'].y
                else:
                    mover.heading = 0
                    mover.pitch = 0

                # Special movement modes.
                # By default, you run ("sprint"), unless you press e, in
                # which case you walk. You can crouch by pressing q; this
                # overrides walking and running. Jump by pressing space.
                # This logic is implemented by the Walking system. Here,
                # only intention is signalled.
                character = entity[Character]
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
            controller = entity[Mover]
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
            Mover,
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
            mover = entity[Mover]
            camera = entity[Camera]
            reorienter = entity[CameraReorientedInput]

            reorienter.node.set_p(model_node, 0)
            mover.translation = model_node.get_relative_vector(
                reorienter.node,
                mover.translation,
            )




class TurningBackToCamera(System):
    '''
        Turns character away from the camera.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.TurningBackToCameraMovement`
            | :class:`wecs.panda3d.movement.Mover''
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.camera.ThirdPersonCamera`
            | :class:`wecs.panda3d.camera.TurntableCamera`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('character_node'),
            Clock,
            AutomaticTurningMovement,
            TurningBackToCameraMovement,
            Mover,
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
            mover = entity[Mover]
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
            if mover.move.xy.length() >= turning.threshold * dt:
                autoturning.alignment = turning.view_axis_alignment
            else:
                autoturning.alignment = 0.0


class DirectlyIndicateDirection(System):
    entity_filters = {
        'character': and_filter([
            Proxy('model'),
            AutomaticTurningMovement,
            TwinStickMovement,
            Mover,
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
        Turns character away from the camera.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.TurningBackToCameraMovement`
            | :class:`wecs.panda3d.character.Mover`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.camera.ThirdPersonCamera`
            | :class:`wecs.panda3d.camera.TurntableCamera`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'character': and_filter([
            Proxy('character_node'),
            Clock,
            AutomaticTurningMovement,
            Mover,
            or_filter([
                WalkingMovement,
                FloatingMovement,
            ]),
        ])
    }
    proxies = {'character_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            mover = entity[Mover]
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
                old_rotation = mover.rotation.x
                mover.rotation.x += angle
                mover.rotation.x = min(
                    mover.rotation.x,
                    max_angle,
                )
                mover.rotation.x = max(
                    mover.rotation.x,
                    -max_angle,
                )
                # Since the camera rotates with the character, we need
                # to counteract that as well.
                delta_rotation = mover.rotation.x - old_rotation
                turning.angle = delta_rotation

                # FIXME: This needs to be its own system
                camera = entity[Camera]
                camera.pivot.set_h(camera.pivot.get_h() - delta_rotation)


class FaceMovement(System):
    entity_filters = {
        'character': and_filter([
            Proxy('geometry_node'),
            Clock,
            Mover,
            FacingMovement,
        ]),
    }
    proxies = {'geometry_node': ProxyType(Geometry, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            geometry_proxy = self.proxies['geometry_node']
            geometry = entity[geometry_proxy.component_type]
            geometry_node = geometry_proxy.field(entity)

            controller = entity[Mover]
            x, y, z = controller.last_translation_speed
            geometry_node.look_at(x, y, 0)


class Jumping(CollisionSystem):
    '''
        Make the character jump.

        Components used :func:`wecs.core.and_filter` 'character'
            | :class:`wecs.panda3d.character.Mover`
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
            Mover,
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
            controller = entity[Mover]
            falling_movement = entity[FallingMovement]
            jumping_movement = entity[JumpingMovement]
            if controller.jumps and falling_movement.ground_contact:
                falling_movement.inertia += jumping_movement.impulse


class WalkSpeedLimiting(System):
    '''
    Applies a slow-down to the character.
    '''
    entity_filters = {
        'character': and_filter([
            Clock,
            Mover,
            WalkingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].game_time
            mover = entity[Mover]
            walking = entity[WalkingMovement]

            v_length = mover.translation.length()
            if v_length > walking.speed * dt:
                mover.translation.normalize()
                mover.translation *= walking.speed * dt

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
            | :class:`wecs.panda3d.character.Mover`
            | :class:`wecs.panda3d.character.Stamina`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'character': and_filter([
            Clock,
            Mover,
            Stamina,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[Mover]
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
