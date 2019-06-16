import sys
import time


class BaseBenchmark:
    def __init__(self, name):
        self.name = name

    def get_mem_usage(self):
        return "", ""

    def setup(self, num_entities, num_components): # pylint: disable=unused-argument
        return 0

    def update_cold(self):
        return 0

    def update_warm(self):
        return 0

    def run(self):
        print('={}='.format(self.name))
        print('==Memory==')
        print('Entity: {}, NullComponent: {}'.format(
            *self.get_mem_usage()
        ))
        print()

        print('==Time==')
        incs = [1, 100, 1000]
        for num_ent in incs:
            for num_comp in incs:
                print('Entities: {}, Components: {}'.format(num_ent, num_comp))
                time_start = time.perf_counter_ns()
                self.setup(num_ent, num_comp)
                time_setup = (time.perf_counter_ns() - time_start) / 100_000

                time_start = time.perf_counter_ns()
                self.update_cold()
                time_update_cold = (time.perf_counter_ns() - time_start) / 100_000

                time_start = time.perf_counter_ns()
                self.update_warm()
                time_update_warm = (time.perf_counter_ns() - time_start) / 100_000

                time_total = time_setup + time_update_cold + time_update_warm
                print('\t{:0.2f}ms (setup: {:0.2f}ms, cold update: {:0.2f}ms, warm update: {:0.2f}ms)'.format(
                    time_total,
                    time_setup,
                    time_update_cold,
                    time_update_warm,
                ))


class SimpleEcsBench(BaseBenchmark):
    def __init__(self):
        import simpleecs
        import simpleecs.components
        self.component_classes = [
            type(
                'NullComponent{}'.format(i),
                simpleecs.components.NullComponent.__bases__,
                dict(simpleecs.components.NullComponent.__dict__),
            )
            for i in range(10_000)
        ]
        self.world = None

        super().__init__('simpleecs')

    def get_mem_usage(self):
        import simpleecs
        import simpleecs.components
        return (
            sys.getsizeof(simpleecs.World().create_entity()),
            sys.getsizeof(simpleecs.components.NullComponent())
        )

    def setup(self, num_entities, num_components):
        import simpleecs
        import simpleecs.systems

        self.world = simpleecs.World()
        self.world.add_system(
            simpleecs.systems.NullSystem(),
        )

        for _ in range(num_entities):
            self.world.create_entity([
                self.component_classes[compnum]
                for compnum in range(num_components)
            ])

    def update_cold(self):
        self.world.update(0)

    def update_warm(self):
        self.world.update(0)


if __name__ == '__main__':
    BENCHMARKS = [
        SimpleEcsBench()
    ]
    for bench in BENCHMARKS:
        bench.run()
