from wecs.panda3d.ai import BehaviorTree


def test_complex_behavior():
    tree = BehaviorTree(
        Priority(
            Sequence
        ),
    )
