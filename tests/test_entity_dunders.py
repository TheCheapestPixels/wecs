import pytest

from fixtures import world, entity, component, Counter


def test_set(world, entity, component):
    entity[Counter] = component


def test_get(world, entity, component):
    entity.add_component(component)
    world._flush_component_updates()
    assert entity[Counter] is component


def test_contains(world, entity, component):
    entity.add_component(component)
    world._flush_component_updates()
    assert Counter in entity


def test_del(world, entity, component):
    entity.add_component(component)
    world._flush_component_updates()
    del entity[Counter]
    world._flush_component_updates()
    assert not entity.has_component(Counter)
