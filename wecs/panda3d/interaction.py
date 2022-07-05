from dataclasses import field

from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue

from wecs.core import Component
from wecs.core import Proxy
from wecs.core import ProxyType
from wecs.core import and_filter

from wecs.panda3d.prototype import Model
from wecs.panda3d.character import CollisionSystem

from wecs.panda3d.constants import INTERACTION_MASK


@Component()
class Interactor:
    tag_name: str = 'interacting'
    node_name: str = 'interactor'
    solids: dict = None
    from_collide_mask: int = INTERACTION_MASK
    into_collide_mask: int = 0
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerQueue)
    debug: bool = False
    # List of possible active interactions
    interactions: list = field(default_factory=list)
    # What actions are available with which entity this frame?
    # Written by the Interacting system.
    action_options: list = field(default_factory=list)


@Component()
class Interactee:
    tag_name: str = 'interacting'
    node_name: str = 'interactee'
    solids: dict = None
    from_collide_mask: int = 0
    into_collide_mask: int = INTERACTION_MASK
    traverser: CollisionTraverser = None
    queue: CollisionHandlerQueue = None
    debug: bool = False
    # List of possible passive interactions
    interactions: list = field(default_factory=list)


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
        self.init_sensors(entity, entity[Interactor])

    def enter_filter_interactee(self, entity):
        self.init_sensors(entity, entity[Interactee])
        component = entity[Interactee]
        for solid in component.solids.values():
            node = solid['node']           
            node.set_python_tag(
                'interactions-entity',
                entity,
            )

    def exit_filter_interactor(self, entity):
        print(f'FIXME: exit_filter_interactor {entity}')

    def exit_filter_interactee(self, entity):
        print(f'FIXME: exit_filter_interactee {entity}')

    def update(self, entities_by_filter):
        for entity in entities_by_filter['interactor']:
            self.run_sensors(entity, entity[Interactor])
            entity[Interactor].action_options = []
            self.check_action_options(entity)

    def check_action_options(self, entity):
        for contact in entity[Interactor].contacts:
            into_np = contact.get_into_node_path()
            into_entity = into_np.get_python_tag('interactions-entity')
            if into_entity == entity:
                pass
            else:
                from_actions = entity[Interactor].interactions
                into_actions = into_entity[Interactee].interactions
                matches = [fa for fa in from_actions
                           if fa in into_actions]
                for match in matches:
                    entity[Interactor].action_options.append(
                        (match, into_entity),
                    )
