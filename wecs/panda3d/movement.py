from math import sqrt
from dataclasses import field

from panda3d.core import Vec2, Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter, or_filter

from .character import CharacterController

from .model import Model
from .model import Clock


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
    move_drain: float = 1
    jump_drain: float = 1
    sprint_drain: float = 1
    crouch_drain: float = 1


@Component()
class AcceleratedMovement:
    accelerate: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    slide: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    brake: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    speed: Vec2 = field(default_factory=lambda:Vec2(0, 0))


class SetStamina(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Stamina,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            stamina = entity[Stamina]
            if stamina.current < stamina.maximum:
                stamina.current += stamina.recovery
            if character.move.x or character.move.y:
                stamina -= stamina.move_drain
            if character.sprints:
                if stamina > stamina.sprint_drain:
                    stamina.current -= stamina.sprint_drain
                else:
                    character.sprints = False
            if crouch:
                if stamina > stamina.crouch_drain:
                    stamina.current -= stamina.crouch_drain
                else:
                    character.crouches = False
            if jump:
                if stamina > stamina.jump_drain:
                    stamina.current -= stamina.jump_drain
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
            def clamp(n, min, max):
                if n < min:
                    n = min
                elif n > max:
                    n = max
                return n

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
