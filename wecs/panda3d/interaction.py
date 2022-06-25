from wecs.core import Component
from wecs.core import Proxy
from wecs.core import ProxyType
from wecs.core import and_filter

from wecs.panda3d.prototype import Model
from wecs.panda3d.character import CollisionSystem


@Component()
class Interactor:
    node_name: str = 'interactor'


@Component()
class Interactee:
    node_name: str = 'interactee'


class Interacting(CollisionSystem):
    '''
        Check for collisions between interactors and interactees.

        Components used :func:`wecs.core.and_filter`
            | :class:`wecs.panda3d.model.Model`
    '''
    entity_filters = {
        'interactor': and_filter([
            Proxy('character_node'),
            Interactor,
        ]),
        'interactee': and_filter([
            Proxy('character_node'),
            Interactee,
        ]),
    }
    proxies = {
        'character_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def enter_filter_interactor(self, entity):
        print(f'enter_filter_interactor {entity}')
        
    def enter_filter_interactee(self, entity):
        print(f'enter_filter_interactee {entity}')
        
    def exit_filter_interactor(self, entity):
        print(f'exit_filter_interactor {entity}')
        
    def exit_filter_interactee(self, entity):
        print(f'exit_filter_interactee {entity}')
        
    def update(self, entities_by_filter):
        for entity in entities_by_filter['interactor']:
            pass
