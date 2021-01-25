from dataclasses import field
import random

from panda3d.core import Vec3

import wecs

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from wecs.panda3d.character import CharacterController
from wecs.panda3d.input import Input


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


class BehaviorTree:
    def __init__(self, root):
        self.root = root

    def __call__(self, entity, *args):
        """Returns True if node has run, False if it can't be run, and
        raises an exception for special cases, e.g. being done with a
        task."""
        self.root(entity, *args)


class Priority:
    def __init__(self, *nodes):
        self.nodes = nodes
        
    def __call__(self, entity, *args):
        for node in self.nodes:
            if node(entity, *args):
                return True
        return False


# Selector: Prioritized list of options.
# Sequence: One child after the other
# Parallel: Executes all children
# FSM
# Attached at runtime: Node behavior is specified re-/set runtime, if no
#   behavior is attached, node fails
# Decorators: Modify node behavior
# * Return
#   * Always succeed
#   * Always fail
#   * Always raise exception
# * Interruptions
#   * Minimum / maximum distance to entity reached
#   * Sensor detects object
#   * Timeout
#   * Uninterruptable: Node will continue to be used until finished,
#     even if higher-priority options become activate in the meantime.
# * Repetition
#   * Loop n times / infinitely
# * Debugging
#   * Tag: Present active tags to user
#   * Message: Log message on activation / deactivation / per frame
#   * Breakpoint: Pause game and inspect behavior


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


def walk_to_entity(entity, target_entity_uid, coordinates=None):
    if coordinates is None:
        coordinates = Vec3(0, 0, 0)

    character = entity[CharacterController]
    target_entity = base.ecs_world.get_entity(target_entity_uid)

    character_node = entity[wecs.panda3d.prototype.Model].node
    target_node = target_entity[wecs.panda3d.prototype.Model].node
    rel_pos = character_node.get_relative_point(target_node, coordinates)
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


class PrintBehaviorOnPlayerCharacters(System):
    entity_filters = {
        'character': [Input, BehaviorAI, CharacterController],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            behavior = entity[BehaviorAI]

            print(behavior.behavior)


class BehaviorInhibitsDirectCharacterControl(System):
    entity_filters = {
        'character': [Input, BehaviorAI, CharacterController],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            behavior = entity[BehaviorAI]
            input = entity[Input]

            if len(behavior.behavior) == 1 and behavior.behavior[0] == 'idle':
                input.contexts.add('character_movement')
            elif 'character_movement' in input.contexts:
                input.contexts.remove('character_movement')
