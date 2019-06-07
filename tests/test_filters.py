import dataclasses

from wecs.core import Component
from wecs.core import and_filter, or_filter, dnf_filter

from fixtures import world, entity


@Component()
class ComponentA:
    pass


@Component()
class ComponentB:
    pass


@Component()
class ComponentC:
    pass


def test_and_filter(entity):
    f = and_filter([ComponentA, ComponentB])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert not f(entity)

    entity.add_component(ComponentB())
    assert f(entity)

    entity.remove_component(ComponentA)
    assert not f(entity)


def test_or_filter(entity):
    f = or_filter([ComponentA, ComponentB])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert f(entity)

    entity.add_component(ComponentB())
    assert f(entity)

    entity.remove_component(ComponentA)
    assert f(entity)

    entity.remove_component(ComponentB)
    assert not f(entity)


def test_dnf_filter(entity):
    f = dnf_filter([[ComponentA], [ComponentB, ComponentC]])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert f(entity)

    entity.add_component(ComponentB())
    assert f(entity)

    entity.add_component(ComponentC())
    assert f(entity)

    entity.remove_component(ComponentA)
    assert f(entity)

    entity.remove_component(ComponentB)
    assert not f(entity)

    entity.remove_component(ComponentC)
    assert not f(entity)
