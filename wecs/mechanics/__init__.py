from wecs.core import Component, System
from wecs.core import and_filter
from wecs.panda3d.model import Clock

from wecs.panda3d import CharacterController
from wecs.panda3d import SprintingMovement
from wecs.panda3d import CrouchingMovement
from wecs.panda3d import JumpingMovement


@Component()
class Stamina:
    current: float = 100.0
    maximum: float = 100.0
    recovery: float = 10
    move_drain: float = 10
    sprint_drain: float = 30
    jump_drain: float = 20


class UpdateStamina(System):
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
