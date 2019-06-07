import sys
import time

import wecs.core as simpleecs

COMP_TEMPLATE = """
@simpleecs.Component()
class NullComponent{}:
    name: str = ""
"""


for i in range(10_000):
    exec(COMP_TEMPLATE.format(i)) # pylint:disable=exec-used


class NullSystem(simpleecs.System):
    entity_filters = {}


def benchmark(num_entities=1, num_components=1):
    print('Entities: {}, Components: {}'.format(num_entities, num_components))
    start = time.perf_counter_ns()
    world = simpleecs.World()
    system = NullSystem()
    world.add_system(system, 0)
    for _ in range(num_entities):
        entity = world.add_entity()
        for j in range(num_components):
            comp = globals()['NullComponent{}'.format(j)]()
            entity.add_component(comp)
    setup_end = time.perf_counter_ns()
    world.update()
    update_end = time.perf_counter_ns()
    world.update()
    warm_update_end = time.perf_counter_ns()

    setup_time = (setup_end - start) / 100_000
    update_time = (update_end - setup_end) / 100_000
    warm_update_time = (warm_update_end - update_end) / 100_000
    total_time = setup_time + update_time
    print('\t{:0.2f}ms (setup: {:0.2f}ms, update: {:0.2f}ms, warm update: {:0.2f}ms)'.format(
        total_time,
        setup_time,
        update_time,
        warm_update_time,
    ))

    return total_time, setup_time, update_time


if __name__ == '__main__':
    print('=Memory=')
    print('Entity: {}, NullComponent: {}'.format(
        sys.getsizeof(simpleecs.World().add_entity()),
        sys.getsizeof(globals()['NullComponent0']())
    ))
    print()

    print('=Time=')
    INCS_ent = [1, 100, 1_000, 10_000]
    INCS_comp = [1, 10, 100]
    for num_ent in INCS_ent:
        for num_comp in INCS_comp:
            benchmark(num_entities=num_ent, num_components=num_comp)
