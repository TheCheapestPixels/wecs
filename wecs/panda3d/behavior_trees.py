from wecs.panda3d.ai import BehaviorAI


class FAILED: pass
class ACTIVE: pass
class DONE: pass


class BehaviorTree:
    """
    Calling a BehaviorTree returns
    * False if running the tree has failed,
    * True if the tree is still running,
    * None if the tree has finished. (This is equivalent to nodes in the
      tree raising `Done`, and done this way to not emit an exception
      that has to be caught.)
    """
    def __init__(self, tree):
        self.tree = tree


    def __call__(self, entity, *args, **kwargs):
        rv = self.tree(entity, *args, **kwargs)
        if rv == DONE:
            return self.done(entity)
        else:
            return rv

    def done(self, entity):
        raise NotImplementedError


class IdleWhenDoneTree(BehaviorTree):
    def done(self, entity):
        entity[BehaviorAI].behavior = ['idle']

class Node:
    def __call__(self, entity, *args, **kwargs):
        raise NotImplementedError

    def reset(self):
        pass


class Action(Node):
    def __init__(self, func):
        self.func = func
        
    def __call__(self, entity, *args, **kwargs):
        return self.func(entity, *args, **kwargs)

    def reset(self):
        pass


class Chain(Node):
    pass


class Priorities(Node):
    def __init__(self, *children):
        self.children = children

    def __call__(self, entity, *args, **kwargs):
        for child in self.children:
            rv = child(entity, *args, **kwargs)
            if rv == ACTIVE or rv == DONE:
                return rv
        return FAILED


class Condition(Node):
    """
    Conditions are decorators that, if a given condition is met, returns
    FIXME. This check is performed either before 
    the subtree is called (precondition) or afterwards (postcondition).
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
    

class SucceedOnCondition:
    def reaction(self):
        return ACTIVE
    

class DoneOnCondition:
    def reaction(self):
        return DONE
    

class FailOnPrecondition(Precondition, FailOnCondition): pass
class SuccessOnPrecondition(Precondition, SucceedOnCondition): pass
class DoneOnPrecondition(Precondition, DoneOnCondition): pass
class FailOnPostcondition(Postcondition, FailOnCondition): pass
class SuccessOnPostcondition(Postcondition, SucceedOnCondition): pass
class DoneOnPostcondition(Postcondition, DoneOnCondition): pass


import wecs

def distance_smaller(target_distance):
    def inner(entity_a, entity_b_uid, coords=None):
        if coords is None:
            coords = Vec3(0, 0, 0)

        node_a = entity_a[wecs.panda3d.prototype.Model].node
        entity_b = base.ecs_world.get_entity(entity_b_uid)
        node_b = entity_b[wecs.panda3d.prototype.Model].node
        distance = node_a.get_relative_point(node_b, coords).length()
        print(distance)
        return distance <= target_distance
    return inner
