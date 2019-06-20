import pytest

from fixtures import world, entity, component, Counter


def test_unflushed_reads(entity, component):
    entity.add_component(component)
    assert entity.has_component(Counter)
    assert entity.get_component(Counter) is component
