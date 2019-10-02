from math import sqrt
from dataclasses import field

from panda3d.core import Vec2, Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter, or_filter

from .character import CharacterController
from .character import CollisionSystem
from .character import FallingMovement

from .model import Model
from .model import Clock
from .model import Scene


@Component()
class ForwardMovement:
    speed: Vec3 = field(default_factory=lambda:Vec3(20,20,20))
    run_threshold: float = 0.5


@Component()
class BackwardMovement:
    speed_multiplier: float = 0.5


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
class AcceleratingMovement:
    accelerate: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    slide: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    brake: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    speed: Vec2 = field(default_factory=lambda:Vec2(0, 0))


@Component()
class Stamina:
    current: float = 100.0
    maximum: float = 100.0
    recovery: float = 1
    move_drain: float = 0.8
    sprint_drain: float = 2
    jump_drain: float = 5


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
                av = (abs(character.move.x)+abs(character.move.y))/2
                stamina.current -= stamina.move_drain * av * dt
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
            if stamina.current < 0:
                stamina.current = 0


class LinearMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            controller   = entity[CharacterController]
            print("translating ", controller.max_move)

            xy_dist = sqrt(controller.move.x**2 + controller.move.y**2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist

            x = controller.move.x * controller.max_move.x * xy_scaling
            y = controller.move.y * controller.max_move.y * xy_scaling
            controller.translation = Vec3(x * dt, y * dt, 0)


class Accelerate(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            AcceleratingMovement,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            character = entity[CharacterController]
            move = entity[AcceleratingMovement]
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
            for a, speed in enumerate(move.speed):
                dest = 0
                if character.move[a] < 0:
                    dest = -1
                elif character.move[a] > 0:
                    dest = 1
                if dest:
                    if ((dest > 0 and move.speed[a] < 0) or
                        (dest < 0 and move.speed[a] > 0)):
                        step = move.brake[a]
                    else:
                        step = move.accelerate[a]
                else:
                    step = move.slide[a]
                move.speed[a] = increment(speed, dest, step)

        xy_dist = sqrt(move.speed.x**2 + move.speed.y**2)
        xy_scaling = 1.0
        if xy_dist > 1:
            xy_scaling = 1.0 / xy_dist
        x = character.max_move.x * xy_scaling
        y = character.max_move.y * xy_scaling
        character.translation.x = x * move.speed.x * dt
        character.translation.y = y * move.speed.y * dt


class Multispeed(System):
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
            elif ForwardMovement in entity:
                character.max_move = entity[ForwardMovement].speed
            if BackwardMovement in entity and character.move.y < 0:
                character.max_move = character.max_move * entity[BackwardMovement].speed_multiplier
            if JumpingMovement in entity  and character.jumps:
                character.max_move = entity[JumpingMovement].speed
            print("setting to ", character.max_move)


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

