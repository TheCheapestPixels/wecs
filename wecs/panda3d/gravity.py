import math

from panda3d.core import Vec3

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
            up = character.gravity * -1

            roll = math.atan(character.gravity.x / character.gravity.z) / (2.0 * math.pi) * 360.0
            model_node.set_r(model_node, roll)

            # FIXME: We now shoud recalculate gravity by also rolling the vector.

            pitch = math.atan(character.gravity.y / character.gravity.z) / (2.0 * math.pi) * 360.0
            model_node.set_p(model_node, -pitch)

            character.gravity = Vec3(0, 0, -character.gravity.length())
