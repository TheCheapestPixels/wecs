import pytest

from fixtures import world
from fixtures import entity
from fixtures import null_component
from fixtures import null_entity
from fixtures import NullComponent


def test_set(world, entity, null_component):
    entity[NullComponent] = null_component
    world._flush_component_updates()


def test_get(world, entity, null_component):
    entity.add_component(null_component)
    world._flush_component_updates()
    assert entity[NullComponent] is null_component
    assert entity.get(NullComponent) is null_component
    assert entity.get("missing") is None
    assert entity.get("missing", "default_value") is "default_value"


def test_contains(world, entity, null_component):
    entity.add_component(null_component)
    assert NullComponent not in entity

    world._flush_component_updates()
    assert NullComponent in entity


def test_del(world, null_entity, null_component):
    del null_entity[NullComponent]
    assert NullComponent in null_entity
    assert null_entity[NullComponent] is null_component

    world._flush_component_updates()
    assert NullComponent not in null_entity
