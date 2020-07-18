import pytest

from wecs.core import Entity, System, Component, World
from wecs.core import and_filter


# Absolute basics

@pytest.fixture
def world():
    return World()


@pytest.fixture
def entity(world):
    return world.create_entity()


# Null stuff

@Component()
class NullComponent:
    pass


@pytest.fixture
def null_component():
    return NullComponent()


@pytest.fixture
def null_entity(world, null_component):
    entity = world.create_entity(null_component)
    world._flush_component_updates()
    return entity


class NullSystem(System):
    entity_filters = {
        "null": and_filter([NullComponent])
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = []
        self.exits = []
        self.updates = []
    
    def enter_filters(self, filters, entity):
        self.entries.append((filters, entity))
    
    def exit_filters(self, filters, entity):
        self.exits.append((filters, entity))

    def update(self, entities_by_filter):
        self.updates.append(entities_by_filter)


class BareNullSystem(NullSystem):
    entity_filters = {
        "null": NullComponent,
    }


@pytest.fixture
def null_system():
    return NullSystem()


@pytest.fixture
def bare_null_system():
    return BareNullSystem()


@pytest.fixture
def null_system_world(world, null_system):
    world.add_system(null_system, 0)
    return world


@pytest.fixture
def bare_null_world(world, bare_null_system):
    world.add_system(bare_null_system, 0)
    return world
