from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.ai import CharacterController


class FAILED: pass
class ACTIVE: pass
class DONE: pass


# Behavior Trees

class BehaviorTree:
    """
    Calling a BehaviorTree returns
    * FAILED if running the tree has failed (it is automatically reset),
    * ACTIVE if the tree is still running,
    
    If the tree has finished (DONE), it resets the tree, then calls its
    `done` method. 
    This is a base class, so you will have to override that method to
    serve your needs.
    """
    def __init__(self, tree):
        self.tree = tree
        self.tree.reset()


    def __call__(self, entity, *args, **kwargs):
        rv = self.tree(entity, *args, **kwargs)
        if rv == DONE:
            self.tree.reset()
            return self.done(entity)
        elif rv == FAILED:
            self.tree.reset()
        return rv

    def done(self, entity):
        raise NotImplementedError


class IdleWhenDoneTree(BehaviorTree):
    """
    A behavior tree that, when it is done, sets the entity's behavior
    to `['idle']`.
    """
    def done(self, entity):
        entity[BehaviorAI].behavior = ['idle']


# Basic Node types

class Node:
    def __call__(self, entity, *args, **kwargs):
        raise NotImplementedError


class Decorator(Node):
    def __call__(self, entity, *args, **kwargs):
        return self.tree(entity, *args, **kwargs)

    def reset(self):
        self.tree.reset()


class Multinode(Node):
    def __init__(self, *children):
        self.children = children
        self.active_child = None
        self.past_child = None

    def reset(self):
        for child in self.children:
            child.reset()


# Leafs (Actions / Tasks)

class Action(Node):
    """
    Action nodes (usually called Tasks) wrap atomic behavior. They are
    the leaves of the behavior tree and have no children.
    Atomic behavior consists of functions that are called with the
    entity as first argument, followed by the arguments that the tree
    has received (subject to mangling by decorators).
    These functions then are simply passed to the node:

        Action(walk_straight)
    """
    def __init__(self, func):
        self.func = func
        
    def __call__(self, entity, *args, **kwargs):
        return self.func(entity, *args, **kwargs)

    def reset(self):
        pass


# Decorators

class DebugPrint(Decorator):
    def __init__(self, text, tree):
        self.text = text
        self.tree = tree

    def __call__(self, entity, *args, **kwargs):
        print(self.text)
        return self.tree(entity, *args, **kwargs)


class DebugPrintOnEnter(Decorator):
    def __init__(self, text, tree):
        self.text = text
        self.tree = tree
        self.fresh = True

    def __call__(self, entity, *args, **kwargs):
        if self.fresh:
            print(self.text)
            self.fresh = False
        return self.tree(entity, *args, **kwargs)

    def reset(self):
        self.fresh = True
        super().reset()


class DebugPrintOnReset(Decorator):
    def __init__(self, text, tree):
        self.text = text
        self.tree = tree

    def reset(self):
        print(self.text)
        super().reset()


class Condition(Decorator):
    """
    Conditions are decorators that, if a given condition is met, returns
    FIXME. This check is performed either before the child node is
    called (precondition) or afterwards (postcondition). If the check
    succeeds, the decorator will return depending on its type (FAILED,
    ACTIVE, or DONE), otherwise it will return what the child node 
    returned.

    The classes to use are thus:
        FailOnPrecondition
        ActiveOnPrecondition
        DoneOnPrecondition
        FailOnPostcondition
        ActiveOnPostcondition
        DoneOnPostcondition

    and are used like this:
        FailOnPrecondition(condition_func, child_tree)

    condition_func will be called with the same arguments as this
    decorator.
    """
    def __init__(self, condition, tree):
        self.condition = condition
        self.tree = tree


class Precondition(Condition):
    def __call__(self, entity, *args, **kwargs):
        if self.condition(entity, *args, **kwargs):
            return self.reaction()
        return self.tree(entity, *args, **kwargs)


class Postcondition(Condition):
    def __call__(self, entity, *args, **kwargs):
        rv = self.tree(entity, *args, **kwargs)
        if self.condition(entity, *args, **kwargs):
            return self.reaction()
        return rv


class FailOnCondition:
    def reaction(self):
        return FAILED
    

class ActiveOnCondition:
    def reaction(self):
        return ACTIVE
    

class DoneOnCondition:
    def reaction(self):
        return DONE
    

class FailOnPrecondition(Precondition, FailOnCondition): pass
class ActiveOnPrecondition(Precondition, ActiveOnCondition): pass
class DoneOnPrecondition(Precondition, DoneOnCondition): pass
class FailOnPostcondition(Postcondition, FailOnCondition): pass
class ActiveOnPostcondition(Postcondition, ActiveOnCondition): pass
class DoneOnPostcondition(Postcondition, DoneOnCondition): pass


class Timer(Decorator):
    """
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
        return ACTIVE
    return inner


def walk_to_entity(entity, target_entity_uid, coords=None):
    func = wecs.panda3d.ai.walk_to_entity
    if coords is None:
        func(entity, target_entity_uid)
    else:
        func(entity, target_entity_uid, coordinates=coords)
    return ACTIVE


def timeout(timeout):
    """
    Condition to be used on Timers. True after the given amount of time
    has elapsed since this decorator became active.
    """
    def inner(timer, *args, **kwargs):
        return timer >= timeout
    return inner


# Multinodes

class Chain(Multinode):
    """
    A Chain (Sequence) node has two or more children that are called in
    order. If any child returns FAILED at any time, the chain also 
    fails.
    
    The Chain calls its first child repeatedly as long as it returns
    ACTIVE. When it returns DONE, the Chain moves on to the next node,
    and so on. When the last child is DONE, so is the Chain.
    """
    def __call__(self, entity, *args, **kwargs):
        if self.active_child is None:
            self.active_child = 0
        for child in self.children[self.active_child:]:
            rv = child(entity, *args, **kwargs)
            if rv == FAILED:
                child.reset()
                return FAILED
            elif rv == ACTIVE:
                return ACTIVE
            else:  # rv == DONE:
                child.reset()
                self.active_child += 1

        # We processed the whole list? Then we really are done.
        self.active_child = None
        return DONE

    def reset(self):
        self.active_child = None
        super().reset()


class Priorities(Multinode):
    """
    The Priorities (a.k.a. Selector) node has two or more children, and
    when called, runs them in order of priority until one has not 
    FAILED. If all fail, so does this node, otherwise it returns what
    the successful node returns (ACTIVE or DONE).
    """
    def __init__(self, *children):
        self.active_child = None
        self.children = children

    def __call__(self, entity, *args, **kwargs):
        for idx, child in enumerate(self.children):
            rv = child(entity, *args, **kwargs)
            if rv == ACTIVE or rv == DONE:
                if idx != self.active_child and self.active_child is not None:
                    previous_child = self.children[self.active_child]
                    previous_child.reset()
                    print("Reset previous choice")
                self.active_child = idx
                return rv
        if self.active_child is not None:
            previous_child = self.children[self.active_child]
            previous_child.reset()
        self.active_child = None
        return FAILED
