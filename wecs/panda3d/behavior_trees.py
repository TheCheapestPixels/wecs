from pychology.behavior_trees import BehaviorTree
from pychology.behavior_trees import Decorator
from pychology.behavior_trees import ActiveOnCondition
from pychology.behavior_trees import FailOnCondition
from pychology.behavior_trees import DoneOnCondition
from pychology.behavior_trees import NodeState

from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.ai import CharacterController


# Behavior Trees

class IdleWhenDoneTree(BehaviorTree):
    """
    A behavior tree that, when it is done, sets the entity's behavior
    to `['idle']`.
    """
    def done(self, entity):
        entity[BehaviorAI].behavior = ['idle']


# Timer decorators

class Timer(Decorator):
    """
    Returns a defined NodeState if the wrapped tree has been run for 
    more than a specified time, using the entity's Clock.game_time to
    increment its counter. Until then, it'll evaluate its subtree
    normally and return its state. For concrete implementations, use
    ActiveTimer, FailTimer, and DoneTimer.
    """
    def __init__(self, condition, tree):
        self.condition = condition
        self.tree = tree
        self.timer = 0.0

    def __call__(self, entity, *args, **kwargs):
        self.timer += entity[wecs.mechanics.clock.Clock].game_time
        if self.condition(self.timer, entity, *args, **kwargs):
            return self.reaction()
        return self.tree(entity, *args, **kwargs)

    def reset(self):
        self.timer = 0.0
        super().reset()


class ActiveTimer(Timer, ActiveOnCondition): pass
class FailTimer(Timer, FailOnCondition): pass
class DoneTimer(Timer, DoneOnCondition): pass


def timeout(timeout):
    """
    Condition to be used on Timers. True after the given amount of time
    has elapsed since this decorator became active.
    """
    def inner(timer, *args, **kwargs):
        return timer >= timeout
    return inner


import wecs
from panda3d.core import Vec3


def distance_smaller(target_distance):
    """
    Condition: Distance between origin of "this" entity and a point in
    the other entity's space.
    """
    def inner(entity_a, entity_b_uid, coords=None):
        if coords is None:
            coords = Vec3(0, 0, 0)

        node_a = entity_a[wecs.panda3d.prototype.Model].node
        entity_b = base.ecs_world.get_entity(entity_b_uid)
        node_b = entity_b[wecs.panda3d.prototype.Model].node
        distance = node_a.get_relative_point(node_b, coords).length()
        return distance <= target_distance
    return inner


def is_pointable(entity, target_entity_uid, coords=None):
    """
    Condition. Is the target entity mouseover-Pointable?
    """
    target_entity = base.ecs_world.get_entity(target_entity_uid)
    return wecs.panda3d.mouseover.Pointable in target_entity


def turn(speed):
    """
    Atomic behavior
    """
    def inner(entity):
        character = entity[CharacterController]
        character.move = Vec3(0, 0, 0)
        character.heading = speed
        character.pitch = 0.0
        character.sprints = False
        character.crouches = False
        character.jumps = False
        return NodeState.ACTIVE
    return inner


def walk_to_entity(entity, target_entity_uid, coords=None):
    func = wecs.panda3d.ai.walk_to_entity
    if coords is None:
        func(entity, target_entity_uid)
    else:
        func(entity, target_entity_uid, coordinates=coords)
    return NodeState.ACTIVE
