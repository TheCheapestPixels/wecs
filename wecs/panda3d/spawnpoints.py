from wecs.core import Component
from wecs.core import System
from wecs.core import Proxy
from wecs.core import ProxyType

from wecs.panda3d.prototype import Model


@Component()
class SpawnMap:
    pass


@Component()
class SpawnAt:
    """
    Adding this component to an entity will make the `Spawn` system
    attach the entity's `model_node` (as defined in 
    `Spawn.proxies['model_node']`
    """
    name: str = None


class Spawn(System):
    entity_filters = {
        'map': [SpawnMap, Proxy('map_node')],
        'spawners': [SpawnAt, Proxy('model_node')],
    }
    proxies = {
        'map_node': ProxyType(Model, 'node'),
        'model_node': ProxyType(Model, 'node'),
    }

    def update(self, entities_by_filter):
        """
        Attach the entities to spawn to their spawn point.
        """
        for entity in entities_by_filter['spawners']:
            spawn_point_name = entity[SpawnAt].name

            # Try finding a node with that name in all the maps. If
            # there should be multiple nodes of that name, then in the
            # first map with one, and the one with the shortest path
            
            # 
            for map_entity in entities_by_filter['map']:
                map_node = self.proxies['map_node'].field(map_entity)
                search_pattern = '**/{}'.format(spawn_point_name)
                spawn_point = map_node.find(search_pattern)
                if not spawn_point.is_empty():
                    model_node = self.proxies['model_node'].field(entity)
                    model_node.reparent_to(spawn_point)
                    # We reparent to the first child so it inherrits the lights
                    model_node.wrt_reparent_to(map_node.get_child(0))
                    break
            else:
                print("Spawn point '{}' not found".format(spawn_point_name))
            del entity[SpawnAt]
