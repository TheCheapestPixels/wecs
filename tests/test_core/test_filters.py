from wecs.core import Component, Proxy, ProxyType
from wecs.core import System, and_filter, or_filter

from fixtures import world, entity
from fixtures import bare_null_world, bare_null_system
from fixtures import NullSystem, NullComponent


@Component()
class ComponentA:
    pass


@Component()
class ComponentB:
    pass


@Component()
class ComponentC:
    pass


def test_and_filter_with_entity(world, entity):
    f = and_filter([ComponentA, ComponentB])
    assert not f(entity)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert not f(entity)

    entity.add_component(ComponentB())
    world._flush_component_updates()
    assert f(entity)

    entity.remove_component(ComponentA)
    world._flush_component_updates()
    assert not f(entity)


def test_and_filter_with_set():
    f = and_filter([ComponentA, ComponentB])

    s = set()
    assert not f(s)

    s = set([ComponentA])
    assert not f(s)

    s = set([ComponentB])
    assert not f(s)

    s = set([ComponentA, ComponentB])
    assert f(s)


def test_or_filter_with_entity(world, entity):
    f = or_filter([ComponentA, ComponentB])
    assert not f(entity)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert f(entity)

    entity.add_component(ComponentB())
    world._flush_component_updates()
    assert f(entity)

    entity.remove_component(ComponentA)
    world._flush_component_updates()
    assert f(entity)

    entity.remove_component(ComponentB)
    world._flush_component_updates()
    assert not f(entity)


def test_or_filter_with_set():
    f = or_filter([ComponentA, ComponentB])

    s = set()
    assert not f(s)

    s = set([ComponentA])
    assert f(s)

    s = set([ComponentB])
    assert f(s)

    s = set([ComponentA, ComponentB])
    assert f(s)


def test_compound_filter_1(world, entity):
    sub_filter_1 = and_filter([ComponentA])
    f = and_filter([sub_filter_1])

    s = set()
    assert not f(s)

    assert not f(entity)

    s = set([ComponentA])
    assert f(s)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert f(entity)


def test_compound_filter_2(world, entity):
    sub_filter_1 = or_filter([ComponentA])
    f = or_filter([sub_filter_1])

    s = set()
    assert not f(s)
    
    assert not f(entity)

    s = set([ComponentA])
    assert f(s)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert f(entity)


def test_compound_filter_3(world, entity):
    sub_filter_1 = and_filter([ComponentA])
    sub_filter_2 = or_filter([ComponentB, ComponentC])
    f = or_filter([sub_filter_1, sub_filter_2])

    s = set()
    assert not f(s)
    
    assert not f(entity)

    s = set([ComponentA])
    assert f(s)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert f(entity)

    s = set([ComponentB])
    assert f(s)

    entity.remove_component(ComponentA)
    entity.add_component(ComponentB())
    world._flush_component_updates()
    assert f(entity)

    s = set([ComponentC])
    assert f(s)

    entity.remove_component(ComponentB)
    entity.add_component(ComponentC())
    world._flush_component_updates()
    assert f(entity)


def test_compound_filter_4(world, entity):
    sub_filter_1 = and_filter([ComponentA])
    sub_filter_2 = or_filter([ComponentB, ComponentC])
    f = and_filter([sub_filter_1, sub_filter_2]) # A and (B or C)

    # Empty
    s = set()
    assert not f(s)

    assert not f(entity)

    # A
    s = set([ComponentA])
    assert not f(s)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert not f(entity)
    entity.remove_component(ComponentA)
    world._flush_component_updates()

    # B
    s = set([ComponentB])
    assert not f(s)

    entity.add_component(ComponentB())
    world._flush_component_updates()
    assert not f(entity)

    # A, B
    s = set([ComponentA, ComponentB])
    assert f(s)

    entity.add_component(ComponentA())
    world._flush_component_updates()
    assert f(entity)

    # A, C
    s = set([ComponentA, ComponentC])
    assert f(s)

    entity.remove_component(ComponentB)
    entity.add_component(ComponentC())
    world._flush_component_updates()
    assert f(entity)

    # C
    s = set([ComponentC])
    assert not f(s)

    entity.remove_component(ComponentA)
    world._flush_component_updates()
    assert not f(entity)


# Test new args syntax

def test_multiarg_creation():
    f = and_filter(ComponentA, or_filter(ComponentB, ComponentC))

    s = set()
    assert not f(s)
    
    s = set([ComponentA])
    assert not f(s)

    s = set([ComponentB])
    assert not f(s)

    s = set([ComponentC])
    assert not f(s)

    s = set([ComponentA, ComponentB])
    assert f(s)

    s = set([ComponentA, ComponentC])
    assert f(s)

    s = set([ComponentB, ComponentC])
    assert not f(s)

    s = set([ComponentA, ComponentB, ComponentC])
    assert f(s)


# Test whether bare component types in entity_filters work as expected

def test_bare_system(bare_null_world, bare_null_system):
    entity = bare_null_world.create_entity(NullComponent())
    bare_null_world._flush_component_updates()
    assert entity in bare_null_system.entities["null"]
    assert len(bare_null_system.entries) == 1
    assert bare_null_system.entries[0] == (['null'], entity)


def test_bare_system_not_adding(bare_null_world, bare_null_system):
    entity_a = bare_null_world.create_entity()
    entity_b = bare_null_world.create_entity(ComponentA())
    bare_null_world._flush_component_updates()
    assert entity_a not in bare_null_system.entities["null"]
    assert entity_b not in bare_null_system.entities["null"]


class ProxyingNullSystem(NullSystem):
    entity_filters = {
        "null": Proxy('null_proxy'),
    }


def test_proxying_system__proxy_is_bare_component(world):
    class BareTypeProxy(ProxyingNullSystem):
        proxies = {
            'null_proxy': NullComponent,
        }

    system = BareTypeProxy()
    world.add_system(system, 0)
    entity = world.create_entity(NullComponent())
    world._flush_component_updates()
    assert entity in system.entities["null"]
    assert len(system.entries) == 1
    assert system.entries[0] == (['null'], entity)


def test_proxying_system__proxy_type(world):
    class NonBareTypeProxy(ProxyingNullSystem):
        proxies = {
            'null_proxy': ProxyType(NullComponent),
        }

    system = NonBareTypeProxy()
    world.add_system(system, 0)
    entity = world.create_entity(NullComponent())
    world._flush_component_updates()
    assert entity in system.entities["null"]
    assert len(system.entries) == 1
    assert system.entries[0] == (['null'], entity)


def test_proxying_system__field_lookup(world):
    token = '123'
    global token_out
    token_out = None

    @Component()
    class TestComponent:
        foo: str = None

    class BareTypeProxy(System):
        entity_filters = {
            'test': Proxy('proxy'),
        }
        proxies = {
            'proxy': ProxyType(TestComponent, 'foo'),
        }

        def update(self, entity_by_filters):
            for entity in entity_by_filters['test']:
                proxy = self.proxies['proxy']
                test = entity[proxy.component_type]

                token = proxy.field(test)

                global token_out
                token_out = token

    system = BareTypeProxy()
    world.add_system(system, 0)
    entity = world.create_entity(TestComponent(foo=token))
    world.update()

    assert token == token_out
