import pytest

from wecs.core import Entity, System, Component, World, and_filter

from fixtures import world, entity, component, system
from fixtures import Counter, IncreaseCount
from fixtures import enabler


def test_create_world():
    world = World()


def test_create_entity(world):
    entity = world.create_entity()


def test_basic_component_handling(world, entity):
    component = Counter(count=0, inited=False)
    assert entity.get_components() == set()
    assert not entity.has_component(Counter)

    entity.add_component(component)
    # flush should not be called directly. It's normally called by
    # world.update(). For testing purposes, however...
    world.flush_component_updates()
    assert entity.has_component(Counter)
    assert entity.get_component(Counter) is component

    entity.remove_component(Counter)
    world.flush_component_updates()
    assert entity.get_components() == set()
    assert not entity.has_component(Counter)


def test_can_not_get_nonexistent_component(entity):
    with pytest.raises(KeyError):
        entity.get_component(Counter)


def test_can_not_remove_nonexistent_component(entity):
    with pytest.raises(KeyError):
        entity.remove_component(Counter)


def test_can_not_add_component_type_multiple_times(entity, component):
    entity.add_component(component)
    with pytest.raises(KeyError):
        entity.add_component(component)


def test_system_handling(world, system):
    assert len(world.get_systems()) == 0
    assert not world.has_system(IncreaseCount)

    world.add_system(system, 0)
    assert world.has_system(IncreaseCount)
    assert world.get_system(IncreaseCount) is system
    assert len(world.get_systems()) == 1

    world.remove_system(IncreaseCount)
    assert not world.has_system(IncreaseCount)
    assert len(world.get_systems()) == 0


def test_can_not_get_nonexistent_system(world, system):
    with pytest.raises(KeyError):
        world.get_system(IncreaseCount)


def test_can_not_remove_nonexistent_system(world, system):
    with pytest.raises(KeyError):
        world.remove_system(IncreaseCount)


def test_can_not_add_system_type_multiple_times(world, system):
    world.add_system(system, 0)
    with pytest.raises(KeyError):
        world.add_system(system, 1)


def test_update_world_when_system_was_added_first(
        world, entity, component, system):
    world.add_system(system, 0)
    entity.add_component(component)
    assert component.count == 0

    world.update()
    assert component.count == 1


def test_update_world_when_component_was_added_first(
        world, entity, component, system):
    entity.add_component(component)
    assert component.count == 0
    world.add_system(system, 0)
    assert component.count == 0

    world.update()
    assert component.count == 1


def test_init_component(world, entity, component, system, enabler):
    world.add_system(system, 0)
    assert system.init_called == 0
    assert system.init_done == 0
    assert not component.inited

    entity.add_component(component)
    world.flush_component_updates()
    assert system.init_called == 1
    assert system.init_done == 0
    assert not component.inited

    entity.add_component(enabler)
    world.flush_component_updates()
    assert system.init_called == 2
    assert system.init_done == 1
    assert component.inited


def test_destroy_component_by_removing_enabler(
        world, entity, component, system, enabler):
    world.add_system(system, 0)
    entity.add_component(component)
    entity.add_component(enabler)
    world.flush_component_updates()
    assert system.destroy_called == 0
    assert system.destroy_done == 0
    assert component.inited

    entity.remove_component(type(enabler))
    world.flush_component_updates()
    assert system.destroy_called == 1
    assert system.destroy_done == 1
    assert not component.inited


def test_destroy_component_by_removing_component(
        world, entity, component, system, enabler):
    world.add_system(system, 0)
    entity.add_component(component)
    entity.add_component(enabler)
    world.flush_component_updates()
    assert system.destroy_called == 0
    assert system.destroy_done == 0
    assert component.inited

    entity.remove_component(type(component))
    world.flush_component_updates()
    assert system.destroy_called == 2 # Both filters fail a once
    assert system.destroy_done == 1 # ...but only one destroyed the component
    assert not component.inited


@Component()
class FooComponent:
    pass


class RemoveFooComponent(System):
    entity_filters = {
        'foos': and_filter([FooComponent]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['foos']:
            # If removal of entities is not deferred until after the
            # system is run, this would lead to a RuntimeError, since
            # it'd be changing the list of entities that we are working
            # on right now.
            entity.remove_component(FooComponent)


class AddFooComponent(System):
    entity_filters = {
        'foos': and_filter([FooComponent]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['foos']:
            # If removal of entities is not deferred until after the
            # system is run, this would lead to a RuntimeError, since
            # it'd be changing the list of entities that we are working
            # on right now.
            entity.remove_component(FooComponent)


def test_deferred_removal_of_components(world, entity):
    world.add_system(RemoveFooComponent(), 0)
    entity.add_component(FooComponent())
    world.update()
