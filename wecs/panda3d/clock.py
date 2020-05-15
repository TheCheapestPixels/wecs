from wecs.core import and_filter
from wecs.mechanics.clock import Clock
from wecs.mechanics.clock import DetermineTimestep
from wecs.panda3d.input import Input


class UpdateClocks(DetermineTimestep):
    input_context = 'clock_control'

    def __init__(self, *args, **kwargs):
        self.entity_filters.update({
            'input': and_filter([
                Clock,
                Input,
            ]),
        })
        super().__init__(*args, **kwargs)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                clock = entity[Clock]
                clock.scaling_factor *= 1 + context['time_zoom'] * 0.01

        super().update(entities_by_filter)
