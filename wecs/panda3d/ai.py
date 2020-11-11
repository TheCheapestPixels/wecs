from dataclasses import field
import random

from panda3d.core import Vec3

import wecs

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from wecs.panda3d.character import CharacterController


def idle(entity):
    character = entity[CharacterController]
    character.move = Vec3(0, 0, 0)
    character.heading = 0.0
    character.pitch = 0.0
    character.sprints = False
    character.crouches = False
    character.jumps = False


def turn_left(entity, speed=1.0):
    character = entity[CharacterController]
    character.move = Vec3(0, 0, 0)
    character.heading = speed
    character.pitch = 0.0
    character.sprints = False
    character.crouches = False
    character.jumps = False


def turn_right(entity, speed=1.0):
    character = entity[CharacterController]
    character.move = Vec3(0, 0, 0)
    character.heading = -speed
    character.pitch = 0.0
    character.sprints = False
    character.crouches = False
    character.jumps = False


@Component()
class ConstantCharacterAI:
    """
    Parameters for the 'constant' behavior.
    Keeps moving in the same direction.

    :param Vec3 move: (0, 0, 0) - relative directional movement speed
    :param float heading: 0.0 - heading
    :param float pitch: 0.0 - pitch
    :param bool sprints: False - is sprinting
    :param bool crouches: False - is crouching
    :param bool jumps: False - starts jumping
    """

    move: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    heading: float = 0.0
    pitch: float = 0.0
    sprints: bool = False
    crouches: bool = False
    jumps: bool = False


def constant(entity):
    ai = entity[ConstantCharacterAI]
    character = entity[CharacterController]

    character.move = ai.move
    character.heading = ai.heading
    character.pitch = ai.pitch
    character.sprints = ai.sprints
    character.crouches = ai.crouches
    character.jumps = ai.jumps


@Component()
class BrownianWalkerAI:
    '''
    Parameters for the 'brownian_walker' behavior.
    Moves randomly.

    :param Vec3 move: (0, 0, 0) - relative directional movement speed
    :param float heading: 0.0 - heading
    :param float heading_jitter: 0.0 - amount heading is randomized each update
    '''
    move: Vec3 = field(default_factory=lambda:Vec3(0, 1, 0))
    heading: float = 1.0
    heading_jitter = 0.1


def brownian_walker(entity):
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


def walk_to_entity(entity, target_entity_uid):
    character = entity[CharacterController]
    target_entity = base.ecs_world.get_entity(target_entity_uid)

    character_node = entity[wecs.panda3d.prototype.Model].node
    target_node = target_entity[wecs.panda3d.prototype.Model].node
    rel_pos = target_node.get_pos(character_node)
    xy_dist = Vec3(rel_pos.x, rel_pos.y, 0)

    character.heading = 0
    character.move = Vec3(0, 0, 0)
    character.pitch = 0
    character.sprints = 0
    character.crouches = 0
    character.jumps = 0

    # If the target is behind you, turn towards it.
    if rel_pos.y < 0:
        if rel_pos.x < 0:
            character.heading = 1
        else:
            character.heading = -1
    else:
        # If the target is outside a tight frontal cone, continue turning.
        if abs(rel_pos.x) * 5 > rel_pos.y:
            if rel_pos.x < 0:
                character.heading = 1
            else:
                character.heading = -1
        # If it is within a somewhat wider cone, move forward.
        if abs(rel_pos.x) * 2 < rel_pos.y:
            character.move = Vec3(0, 0.2, 0)


def behaviors():
    return dict(
        idle=idle,
        turn_left=turn_left,
        turn_right=turn_right,
        constant=constant,
        brownian_walker=brownian_walker,
        walk_to_entity=walk_to_entity,
    )


@Component()
class BehaviorAI:
    '''
    Preprogrammed behaviors.
    '''
    behavior: str = field(default_factory=lambda: list(['idle']))
    behaviors: dict = field(default_factory=behaviors)


class Think(System):
    '''
    A System updating AI components.
    '''
    entity_filters = {
        'behavior': [
            CharacterController,
            BehaviorAI,
        ],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['behavior']:
            ai = entity[BehaviorAI]
            behavior = ai.behavior[0]
            args = ai.behavior[1:]

            ai.behaviors[behavior](entity, *args)
