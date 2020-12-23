from wecs.core import System
from wecs.core import Component
from wecs.core import Proxy
from wecs.core import ProxyType

from wecs.panda3d.prototype import Model
from wecs.panda3d.character import CharacterController


class AdjustGravity(System):
    entity_filters = {
        'character': [
            Proxy('model_node'),
            CharacterController,
        ],
    }
    proxies = {'model_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            model_node = self.proxies['model_node'].field(entity)
            
            gravity_node = base.render
            attractor = model_node.get_pos(gravity_node)
            attractor.y = 0.0
            attractor.normalize()
            attractor *= 9.81
            local_gravity = model_node.get_relative_vector(
                gravity_node,
                attractor,
            )
            character.gravity = local_gravity
                


class ErectCharacter(System):
    entity_filters = {
        'character': [
            Proxy('model_node'),
            CharacterController,
        ],
    }
    proxies = {'model_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            model_node = self.proxies['model_node'].field(entity)

            #model_node.heads_up(Vec3(0, 1, 0), character.gravity * -1)
