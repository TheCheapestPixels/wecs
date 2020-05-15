import pytest

from wecs.core import Entity, System, Component, World
from wecs.core import and_filter

from fixtures import world
from fixtures import entity
from fixtures import NullComponent
from fixtures import null_component
from fixtures import NullSystem
from fixtures import null_system
from fixtures import null_system_world
from fixtures import null_entity


def test_create_world():
    world = World()


def test_create_entity(world):
    entity = world.create_entity()


def test_add_component(world, entity):
    component = NullComponent()
    entity[NullComponent] = component
    assert entity in world._addition_pool
    with pytest.raises(KeyError):
        entity[NullComponent]

    world._flush_component_updates()
    assert entity not in world._addition_pool
    assert entity[NullComponent] is component


def test_remove_component(world, entity):
    component = NullComponent()
    entity[NullComponent] = component
    world._flush_component_updates()

    del entity[NullComponent]
    assert entity in world._removal_pool
    assert entity[NullComponent] is component

    world._flush_component_updates()
    assert entity not in world._removal_pool
    with pytest.raises(KeyError):
        entity[NullComponent]


def test_addition_to_system__system_first(world, null_system):
    world.add_system(null_system, 0)
    entity = world.create_entity(NullComponent())
    world._flush_component_updates()
    assert entity in null_system.entities["null"]
    assert len(null_system.entries) == 1
    assert null_system.entries[0] == (['null'], entity)


def test_addition_to_system__entity_first(world, null_system):
    entity = world.create_entity(NullComponent())
    world._flush_component_updates()
    world.add_system(null_system, 0)
    assert entity in null_system.entities['null']
    assert len(null_system.entries) == 1
    assert null_system.entries[0] == (['null'], entity)


def test_entity_dropped_from_system_filter(null_system_world, null_system, null_entity):
    # Preconditions
    assert null_entity in null_system.entities['null']
    assert len(null_system.entries) == 1
    assert null_system.entries[0] == (['null'], null_entity)

    # Change
    del null_entity[NullComponent]
    null_system_world._flush_component_updates()

    # Postconditions
    assert null_system.entities['null'] == set()
    assert len(null_system.exits) == 1
    assert null_system.exits[0] == (['null'], null_entity)


def test_remove_system(world, null_system):
    entity = world.create_entity(NullComponent())
    world._flush_component_updates()
    world.add_system(null_system, 0)

    world.remove_system(NullSystem)
    assert null_system.entities['null'] == set()
    assert len(null_system.exits) == 1
    assert null_system.entries[0] == (['null'], entity)
    assert world.systems == {}
    assert not world.has_system(NullSystem)


def test_system_update(null_system_world, null_system, null_entity):
    null_system_world.update()
    assert len(null_system.updates) == 1
    assert null_system.updates[0] == {'null': set([null_entity])}


def test_system_filters_from_bare_component(world):
    class BareSystem(System):
        entity_filters = {
            'bare': NullComponent,
        }

# Edge Cases

def test_can_not_get_nonexistent_component(entity):
    with pytest.raises(KeyError):
        entity[NullComponent]


def test_can_not_remove_nonexistent_component(entity):
    with pytest.raises(KeyError):
        del entity[NullComponent]


def test_can_not_add_component_type_multiple_times(entity, null_component):
    entity.add_component(null_component)
    with pytest.raises(KeyError):
        entity.add_component(null_component)


def test_can_not_get_nonexistent_system(world):
    with pytest.raises(KeyError):
        world.get_system(NullSystem)


def test_can_not_remove_nonexistent_system(world):
    with pytest.raises(KeyError):
        world.remove_system(NullSystem)


def test_can_not_add_system_type_multiple_times(world):
    world.add_system(NullSystem, 0)
    with pytest.raises(KeyError):
        world.add_system(NullSystem, 1)
