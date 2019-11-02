from dataclasses import field

from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .character import CharacterController


@Component()
class ConstantCharacterAI:
    move: Vec3 = field(default_factory=lambda:Vec3(0,0,0))
    heading: float = 0.0
    pitch: float = 0.0
    sprints: bool = False
    crouches: bool = False
    jumps: bool = False


class Think(System):
    entity_filters = {
        'constant': and_filter([
            CharacterController,
            ConstantCharacterAI,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['constant']:
            character = entity[CharacterController]
            ai = entity[ConstantCharacterAI]

            character.move = ai.move
            character.heading = ai.heading
            character.pitch = ai.pitch
            character.sprints = ai.sprints
            character.crouches = ai.crouches
            character.jumps = ai.jumps
