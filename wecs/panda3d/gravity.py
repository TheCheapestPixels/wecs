import math
from dataclasses import field

from panda3d.core import Vec3

from wecs.core import System
from wecs.core import Component
from wecs.core import Proxy
from wecs.core import ProxyType

from wecs.panda3d.prototype import Model
from wecs.panda3d.character import CharacterController


@Component()
class GravityMap:
    """
    Either this entity's `Model` contains gravity nodes which will be
    looked up by name, or the nodes are given explicitly.
    """
    nodes: dict = field(default_factory=dict)
    node_names: list = field(default_factory=lambda: ["gravity"])


@Component()
class GravityMovement:
    """
    Entity uses gravity nodes on maps to determine its gravity vector.

    :param:`node_names`: List of names of gravity nodes to use.
    """
    node_names: list = field(default_factory=lambda: ["gravity"])

class AdjustGravity(System):
    entity_filters = {
        'map': [
            Proxy('model_node'),
            GravityMap,
        ],
        'character': [
            Proxy('model_node'),
            CharacterController,
            GravityMovement,
        ],
    }
    proxies = {'model_node': ProxyType(Model, 'node')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.known_maps = set()

    def enter_filter_map(self, entity):
        self.known_maps.add(entity)

        gravity_map = entity[GravityMap]
        model_node = self.proxies['model_node'].field(entity)

        for node_name in gravity_map.node_names:
            # FIXME: Respect multiple names
            node = model_node.find(f'**/{node_name}')
            # FIXME: Raise warning if node not found
            if not node.is_empty():
                # FIXME: Maybe don't overwrite given nodes?
                gravity_map.nodes[node_name] = node

    def exit_filter_map(self, entity):
        self.known_maps.remove(entity)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            gravity = entity[GravityMovement]
            model_node = self.proxies['model_node'].field(entity)

            # FIXME: We just use the first given name, and the first
            # node found. Both should deal with multiples.
            gravity_name = gravity.node_names[0]
            for map_entity in self.known_maps:
                gravity_map = map_entity[GravityMap]
                if gravity_name in gravity_map.nodes:
                    gravity_node = gravity_map.nodes[gravity_name]
                    attractor = model_node.get_pos(gravity_node)
                    attractor.y = 0.0
                    attractor.normalize()
                    attractor *= 9.81
                    local_gravity = model_node.get_relative_vector(
                        gravity_node,
                        attractor,
                    )
                    character.gravity = local_gravity
                    break
                


class ErectCharacter(System):
    entity_filters = {
        'character': [
            Proxy('model_node'),
            CharacterController,
            GravityMovement,
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
