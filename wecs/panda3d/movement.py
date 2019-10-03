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


def clamp(n, floor, ceiling):
    return min(ceiling, max(n, floor))


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
class AcceleratingMovement:
    accelerate: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    slide: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    brake: Vec2 = field(default_factory=lambda:Vec2(1, 1))
    speed: Vec2 = field(default_factory=lambda:Vec2(0, 0))


@Component()
class Stamina:
    current: float = 100.0
    maximum: float = 100.0
    recovery: float = 10
    move_drain: float = 10
    sprint_drain: float = 30
    jump_drain: float = 20


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
            xy_dist = sqrt(controller.move.x**2 + controller.move.y**2)
            xy_scaling = 1.0
            if xy_dist > 1:
                xy_scaling = 1.0 / xy_dist
            x = controller.move.x * controller.max_move.x * xy_scaling
            y = controller.move.y * controller.max_move.y * xy_scaling
            controller.translation = Vec3(x * dt, y * dt, 0)


class Accelerating(System):
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
            for a, speed in enumerate(move.speed):
                moving = character.move[a]
                max_move = character.max_move[a]
                if moving:
                    if speed < max_move*moving:
                        step = move.accelerate[a]
                        if speed < 0:
                            step = move.brake[a]
                    elif speed > max_move*moving:
                        step = -move.accelerate[a]
                        if speed > 0:
                            step = -move.brake[a]
                    else: step = 0
                else:
                    slide = move.slide[a]
                    if speed > slide:
                        step = -slide
                    elif speed < -slide:
                        step = slide   
                    else: 
                        step = 0
                        move.speed[a] = 0
                move.speed[a] += step
        mx, my = move.speed.x, move.speed.y
        xy_dist = sqrt(character.move.x**2 + character.move.y**2)
        xy_scaling = 1.0
        if xy_dist > 1:
            xy_scaling = 1.0 / xy_dist
        x = mx * xy_scaling
        y = my * xy_scaling
        character.translation = Vec3(x * dt, y * dt, 0)


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
            elif WalkingMovement in entity:
                if character.move.y < 0:
                    multiplier = entity[WalkingMovement].backwards_multiplier
                else:
                    multiplier = 1
                character.max_move = entity[WalkingMovement].speed * multiplier
            if JumpingMovement in entity  and character.jumps:
                character.max_move = entity[JumpingMovement].speed


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

