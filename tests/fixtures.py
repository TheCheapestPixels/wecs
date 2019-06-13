import pytest

from wecs.core import Entity, System, Component, World
from wecs.core import and_filter


@Component()
class Counter:
    count: int
    inited: bool


@Component()
class Enabler:
    pass


class IncreaseCount(System):
    entity_filters = {
        'has_counter': and_filter([Counter]),
        'init_enabled': and_filter([Counter, Enabler]),
    }

    def __init__(self):
        System.__init__(self)
        self.init_called = 0
        self.init_done = 0
        self.destroy_called = 0
        self.destroy_done = 0

    def init_entity(self, filter_name, entity):
        self.init_called += 1
        if filter_name == 'init_enabled':
            entity.get_component(Counter).inited = True
            self.init_done += 1

    def destroy_entity(self, filter_name, entity, components_by_type):
        self.destroy_called += 1
        if filter_name == 'has_counter':
            components_by_type[Counter].inited = False
            self.destroy_done += 1
        elif filter_name == 'init_enabled':
            if entity.has_component(Counter):
                entity.get_component(Counter).inited = False
                self.destroy_done += 1

    def update(self, filtered_entities):
        for entity in filtered_entities['has_counter']:
            entity.get_component(Counter).count += 1


@pytest.fixture
def world():
    return World()


@pytest.fixture
def entity(world):
    return world.create_entity()


@pytest.fixture
def component():
    return Counter(count=0, inited=False)


@pytest.fixture
def enabler():
    return Enabler()


@pytest.fixture
def system():
    return IncreaseCount()
