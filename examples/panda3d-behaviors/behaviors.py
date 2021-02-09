import wecs
#from wecs.panda3d import behavior_trees

from wecs.panda3d.behavior_trees import IdleWhenDoneTree
from wecs.panda3d.behavior_trees import Action
from wecs.panda3d.behavior_trees import Priorities
from wecs.panda3d.behavior_trees import Chain
from wecs.panda3d.behavior_trees import DebugPrint
from wecs.panda3d.behavior_trees import DebugPrintOnEnter
from wecs.panda3d.behavior_trees import DebugPrintOnReset
from wecs.panda3d.behavior_trees import DoneOnPrecondition
from wecs.panda3d.behavior_trees import FailOnPrecondition
from wecs.panda3d.behavior_trees import DoneTimer


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
