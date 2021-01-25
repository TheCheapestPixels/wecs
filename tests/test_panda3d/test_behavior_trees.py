from wecs.panda3d.behavior_trees import BehaviorTree as BehaviorTreeBase
from wecs.panda3d.behavior_trees import ACTIVE
from wecs.panda3d.behavior_trees import DONE
from wecs.panda3d.behavior_trees import Action
from wecs.panda3d.behavior_trees import Priorities
from wecs.panda3d.behavior_trees import DoneOnPostcondition
from wecs.panda3d.behavior_trees import FailOnPrecondition


class BehaviorTree(BehaviorTreeBase):
    def done(self):
        return DONE


def set_foo_to_true(entity):
    entity['foo'] = True
    return DONE

    
def increment_foo(entity):
    entity['foo'] += 1
    return ACTIVE


def foo_is_five(entity):
    return entity['foo'] == 5


def test_tree_1():
    blackboard = dict(foo=False)

    tree = BehaviorTree(Action(set_foo_to_true))

    assert tree(blackboard) is DONE
    assert blackboard['foo']


def test_tree_2():
    blackboard = dict(foo=0)

    tree = BehaviorTree(
        DoneOnPostcondition(
            foo_is_five,
            Action(increment_foo),
        ),
    )

    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is DONE
    assert blackboard['foo'] == 5


def test_tree_3():
    blackboard = dict(foo=0)

    tree = BehaviorTree(
        Priorities(
            FailOnPrecondition(
                foo_is_five,
                Action(increment_foo),
            ),
            Action(set_foo_to_true),
        ),
    )

    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is ACTIVE
    assert tree(blackboard) is DONE
    assert blackboard['foo'] is True
