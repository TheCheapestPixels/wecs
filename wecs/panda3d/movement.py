from math import sqrt
from dataclasses import field

from panda3d.core import Vec2, Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter, or_filter

from .character import CharacterController
from .character import FallingMovement

from .model import Model
from .model import Clock


@Component()
class JumpingMovement:
    stamina_drain: float = 0
    impulse: bool = field(default_factory=lambda:Vec3(0, 0, 5))


@Component()
class SprintMovement:
    speed_multiplier: float = 1.5


@Component()
class CrouchMovement:
    speed_multiplier: float = 0.3
    height: float = 0.4


@Component()
class Stamina:
    current: 	float = 100.0
    maximum:	float = 100.0
    recovery: 	float = 1
    move_drain: float = 0.6
    crouch_drain: float = 0.4
    sprint_drain: float = 1
    jump_drain: float = 1


@Component()
class AcceleratedMovement:
    accelerate: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    slide: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    brake: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    speed: Vec2 = field(default_factory=lambda:Vec2(0, 0))


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


class SetStamina(System):
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
            stamina.current += stamina.recovery * dt
            if stamina.current > stamina.maximum:
                stamina.current = stamina.maximum
            if character.move.x or character.move.y:
                stamina -= stamina.move_drain * dt
            if character.sprints:
                if stamina > stamina.sprint_drain * dt:
                    stamina.current -= stamina.sprint_drain * dt
                else:
                    character.sprints = False
            elif character.crouches:
                if stamina > stamina.crouch_drain * dt:
                    stamina.current -= stamina.crouch_drain * dt
                else:
                    character.crouches = False
            if jump:
                if stamina > stamina.jump_drain * dt:
                    stamina.current -= stamina.jump_drain * dt
                else:
                    character.jumps = False


class Accelerate(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            AcceleratedMovement,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            character   = entity[CharacterController]
            acc	 = entity[AcceleratedMovement]
            def clamp(x, floor, ceiling): 
                return min(ceiling, max(x, floor))

            def increment(n, dest, step):
                if n < dest-step:
                    n += step
                elif n > dest+step:
                    n -= step
                else:
                    n = dest
                return n

            for a, speed in enumerate(acc.speed):
                dest = 0
                if character.move[a] < 0:
                    dest = -1
                elif character.move[a] > 0:
                    dest = 1
                if dest:
                    if ((dest > 0 and acc.speed[a] < 0) or
                        (dest < 0 and acc.speed[a] > 0)):
                        step = acc.brake[a]
                    else:
                        step = acc.accelerate[a]
                else:
                    step = acc.slide[a]
                acc.speed[a] = increment(speed, dest, step)
        xy_dist = sqrt(acc.speed.x**2 + acc.speed.y**2)
        xy_scaling = 1.0
        if xy_dist > 1:
            xy_scaling = 1.0 / xy_dist
        x = character.max_move.x * character.move_multiplier * xy_scaling
        y = character.max_move.y * character.move_multiplier * xy_scaling
        character.translation.x = x * acc.speed.x * dt
        character.translation.y = y * acc.speed.y * dt


class Multispeed(System):
    entity_filters = {
        'character': or_filter([
            CharacterController,
            SprintMovement,
            CrouchMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character   = entity[CharacterController]
            sprint      = entity[SprintMovement]
            crouch	= entity[CrouchMovement]

            character.move_multiplier = 1
            if character.sprints:
                character.move_multiplier = sprint.speed_multiplier
            if character.crouches:
                character.move_multiplier = crouch.speed_multiplier
            if character.jumps:
                character.move_multiplier = crouch.speed_multiplier