import pytest

from wecs.core import World
from wecs.panda3d.core import ECSShowBase
from wecs.panda3d.model import Model
from wecs.panda3d.model import Geometry

from wecs.panda3d.model import SetupModels
from wecs.panda3d.model import UpdateSprites
from wecs.panda3d.model import ManageGeometry
from wecs.panda3d.model import Sprite
from wecs.mechanics.clock import Clock

from panda3d.core import NodePath


@pytest.fixture
def ecs_base():
    ECSShowBase()
    base.ecs_world.add_system(SetupModels(), 0)
    base.ecs_world.add_system(UpdateSprites(), 1)
    base.ecs_world.add_system(ManageGeometry(), 3)
    yield
    assert isinstance(base.ecs_world, World)
    base.destroy()


@pytest.fixture
def entity(ecs_base):
    entity =  base.ecs_world.create_entity(
        Clock(),
        Model(),
        Geometry(),
        Sprite(),
    )
    base.ecs_world.update()
    return entity


def test_manage_geometry(entity):
    assert entity[Geometry].node.get_parent() == entity[Model].node
    assert entity[Sprite].node.get_parent() == entity[Geometry].node
    entity[Geometry].nodes.remove(entity[Sprite].node)
    base.ecs_world.update()
    assert entity[Sprite].node.get_parent() != entity[Geometry].node
