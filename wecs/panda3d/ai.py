from dataclasses import field
import random

from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .character import CharacterController


@Component()
class ConstantCharacterAI:
    '''
    Keeps moving in the same direction.

    :param Vec3 move: (0, 0, 0) - relative directional movement speed
    :param float heading: 0.0 - heading
    :param float pitch: 0.0 - pitch
    :param bool sprints: False - is sprinting
    :param bool crouches: False - is crouching
    :param bool jumps: False - starts jumping
    '''

    move: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    heading: float = 0.0
    pitch: float = 0.0
    sprints: bool = False
    crouches: bool = False
    jumps: bool = False


@Component()
class BrownianWalkerAI:
    '''
    Moves randomly.

    :param Vec3 move: (0, 0, 0) - relative directional movement speed
    :param float heading: 0.0 - heading
    :param float heading_jitter: 0.0 - amount heading is randomized each update
    '''
    move: Vec3 = field(default_factory=lambda:Vec3(0, 1, 0))
    heading: float = 1.0
    heading_jitter = 0.1


class Think(System):
    '''
    A System updating AI components.

    '''
    entity_filters = {
        'constant': and_filter([
            CharacterController,
            ConstantCharacterAI,
        ]),
        'brownian_walker': and_filter([
            CharacterController,
            BrownianWalkerAI,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['constant']:
            ai = entity[ConstantCharacterAI]
            character = entity[CharacterController]

            character.move = ai.move
            character.heading = ai.heading
            character.pitch = ai.pitch
            character.sprints = ai.sprints
            character.crouches = ai.crouches
            character.jumps = ai.jumps

        for entity in entities_by_filter['brownian_walker']:
            ai = entity[BrownianWalkerAI]
            character = entity[CharacterController]

            character.move = Vec3(
                ai.move.x * random.random(),
                ai.move.y * random.random(),
                ai.move.z * random.random(),
            )
            ai.heading += ai.heading_jitter * (random.random() - 0.5) * 2
            if ai.heading > 1:
                ai.heading -= 2
            elif ai.heading < -1:
                ai.heading += 2
            character.heading = ai.heading
            character.pitch = 0
            character.sprints = 0
            character.crouches = 0
            character.jumps = 0
