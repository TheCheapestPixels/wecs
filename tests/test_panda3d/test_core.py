import pytest

from panda3d.core import load_prc_file_data

from wecs.core import World
from wecs.core import System
from wecs.panda3d.core import ECSShowBase


load_prc_file_data("", "window-type none");


def test_panda3d_setup():
    ECSShowBase()
    base.destroy()


@pytest.fixture
def ecs_base():
    ECSShowBase()
    yield
    assert isinstance(base.ecs_world, World)
    base.destroy()


def test_adding_system(ecs_base):
    class DemoSystem(System):
        entity_filters = {}
    task = base.add_system(DemoSystem(), 23)
    assert task.sort == 23
    assert task.priority == 0
    assert task in base.task_mgr.getAllTasks()
