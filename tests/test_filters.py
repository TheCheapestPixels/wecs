import dataclasses

from wecs.core import Component
from wecs.core import and_filter, or_filter

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


def test_compound_filter_1(entity):
    sub_filter_1 = and_filter([ComponentA])
    f = and_filter([sub_filter_1])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert f(entity)


def test_compound_filter_2(entity):
    sub_filter_1 = or_filter([ComponentA])
    f = or_filter([sub_filter_1])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert f(entity)


def test_compound_filter_3(entity):
    sub_filter_1 = and_filter([ComponentA])
    sub_filter_2 = or_filter([ComponentB, ComponentC])
    f = or_filter([sub_filter_1, sub_filter_2])
    assert not f(entity)

    entity.add_component(ComponentA())
    assert f(entity)
    entity.remove_component(ComponentA)

    entity.add_component(ComponentB())
    assert f(entity)
    entity.remove_component(ComponentB)

    entity.add_component(ComponentC())
    assert f(entity)
    entity.remove_component(ComponentC)


def test_compound_filter_4(entity):
    sub_filter_1 = and_filter([ComponentA])
    sub_filter_2 = or_filter([ComponentB, ComponentC])
    f = and_filter([sub_filter_1, sub_filter_2]) # A and (B or C)
    assert not f(entity)

    entity.add_component(ComponentA())
    # A
    assert not f(entity)
    entity.remove_component(ComponentA)

    entity.add_component(ComponentB())
    # B
    assert not f(entity)

    entity.add_component(ComponentA())
    # A, B
    assert f(entity)

    entity.remove_component(ComponentB)
    entity.add_component(ComponentC())
    # A, C
    assert f(entity)

    entity.remove_component(ComponentA)
    # C
    assert not f(entity)
