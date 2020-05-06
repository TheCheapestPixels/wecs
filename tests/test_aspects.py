import pytest

from wecs.core import Component
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.aspects import MetaAspect

from fixtures import world


@Component()
class Component_A:
    i: int = 0


@Component()
class Component_B:
    i: int = 0


@Component()
class Component_C:
    pass


def test_name():
    aspect = Aspect([], name="foo")
    assert repr(aspect) == "foo"


def test_no_name():
    aspect = Aspect([])
    assert repr(aspect).startswith("<")


def test_aspect_from_components():
    aspect = Aspect([Component_A])
    assert Component_A in aspect


def test_aspect_from_aspect():
    aspect_1 = Aspect([Component_A])
    aspect_2 = Aspect([aspect_1])
    assert Component_A in aspect_2


def test_aspect_from_multiple_components_same_dict():
    aspect = Aspect([Component_A, Component_B])
    assert Component_A in aspect
    assert Component_B in aspect


def test_aspect_from_multiple_components_different_dicts():
    aspect = Aspect([Component_A, Component_B])
    assert Component_A in aspect
    assert Component_B in aspect


def test_aspect_from_multiple_aspects():
    aspect_1 = Aspect([Component_A])
    aspect_2 = Aspect([Component_B])
    aspect_3 = Aspect([aspect_1, aspect_2])
    assert Component_A in aspect_3
    assert Component_B in aspect_3


def test_aspect_from_multiple_components_different_dicts():
    aspect = Aspect([Component_A, Component_B])
    assert Component_A in aspect
    assert Component_B in aspect


def test_aspect_from_mixed_args():
    aspect_1 = Aspect([Component_A])
    aspect_2 = Aspect([Component_B, aspect_1])
    assert Component_A in aspect_2
    assert Component_B in aspect_2


def test_clashing_args():
    with pytest.raises(ValueError):
        aspect = Aspect([Component_A, Component_A])

def test_clashing_aspects():
    aspect_1 = Aspect([Component_A, Component_B])
    aspect_2 = Aspect([Component_B])
    with pytest.raises(ValueError):
        aspect_3 = Aspect([aspect_1, aspect_2])


def test_create_components():
    aspect = Aspect([Component_A])
    [components_a] = aspect()
    [components_b] = [Component_A()]
    assert components_a.i == components_b.i


def test_create_with_overrides_on_aspect():
    aspect = Aspect(
        [Component_A],
        overrides={
            Component_A: dict(i=1),
        },
    )
    [component] = aspect()
    assert component.i == 1


def test_create_with_overrides_on_creation():
    aspect = Aspect([Component_A])
    [component] = aspect(overrides={Component_A: dict(i=1)})
    assert component.i == 1

def test_create_with_override_for_missing_component():
    with pytest.raises(ValueError):
        Aspect(
            [Component_A],
            overrides={
                Component_B: dict(i=1),
            },
        )


def test_adding_aspect_to_entity(world):
    aspect = Aspect([Component_A])
    entity = world.create_entity()
    aspect.add(entity)
    world._flush_component_updates()
    assert Component_A in entity


def test_adding_clashing_aspect_to_entity(world):
    aspect = Aspect([Component_A])
    entity = world.create_entity(Component_A())
    with pytest.raises(KeyError):
        aspect.add(entity)


def test_aspect_in_entity(world):
    aspect = Aspect([Component_A])
    entity = world.create_entity()
    aspect.add(entity)
    world._flush_component_updates()
    assert aspect.in_entity(entity)


def test_aspect_not_in_entity(world):
    entity = world.create_entity()
    aspect = Aspect([Component_A])
    assert not aspect.in_entity(entity)


def test_remove_aspect_from_entity(world):
    aspect = Aspect([Component_A])
    entity = world.create_entity(*aspect())
    world._flush_component_updates()
    assert aspect.in_entity(entity)
    components = aspect.remove(entity)
    world._flush_component_updates()
    assert not aspect.in_entity(entity)
    assert Component_A not in entity
    assert len(components) == 1
    assert isinstance(components[0], Component_A)


def test_remove_aspect_from_entity_that_does_not_have_it(world):
    aspect = Aspect([Component_A])
    entity = world.create_entity()
    with pytest.raises(ValueError):
        aspect.remove(entity)


def test_factory_func():
    class Foo:
        pass
    f = factory(lambda:Foo())
    a = f()
    b = f()
    assert isinstance(a, Foo)
    assert isinstance(b, Foo)
    assert a is not b


def test_create_aspect_with_factory_function_defaults(world):
    class Foo:
        pass
    aspect = Aspect([Component_A],
                    overrides={
                        Component_A: dict(i=factory(lambda:1)),
                    },
    )
    [a] = aspect()
    assert a.i == 1
