from pychology.behavior_trees import Action
from pychology.behavior_trees import Priorities
from pychology.behavior_trees import Chain
from pychology.behavior_trees import DoneOnPrecondition
from pychology.behavior_trees import FailOnPrecondition

import wecs

from wecs.panda3d.behavior_trees import DoneTimer
from wecs.panda3d.behavior_trees import IdleWhenDoneTree


def idle():
    return IdleWhenDoneTree(
        Chain(
            DoneTimer(
                wecs.panda3d.behavior_trees.timeout(3.0),
                Action(wecs.panda3d.behavior_trees.turn(1.0)),
            ),
            DoneTimer(
                wecs.panda3d.behavior_trees.timeout(3.0),
                Action(wecs.panda3d.behavior_trees.turn(-1.0)),
            ),
        ),
    )


def walk_to_entity():
    return IdleWhenDoneTree(
        Priorities(
            FailOnPrecondition(
                wecs.panda3d.behavior_trees.is_pointable,
                DoneOnPrecondition(
                    wecs.panda3d.behavior_trees.distance_smaller(1.5),
                    Action(wecs.panda3d.behavior_trees.walk_to_entity),
                ),
            ),
            DoneOnPrecondition(
                wecs.panda3d.behavior_trees.distance_smaller(0.01),
                Action(wecs.panda3d.behavior_trees.walk_to_entity),
            ),
        ),
    )
