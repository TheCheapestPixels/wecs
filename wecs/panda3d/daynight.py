from dataclasses import field

from panda3d.core import Vec2
from panda3d.core import NodePath
from panda3d.core import DirectionalLight

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from wecs.mechanics.clock import Clock
from wecs.mechanics.clock import Calendar

from .model import Scene
from .model import Model


def tod_color(tod, colors):
    states = len(colors)-1 # How many colors to blend to/from
    color_index = int(tod*states)%states # When was the last color?
    color = list(colors[color_index]) # What color is it?
    next_color = colors[(color_index+1)%states] # what's the next color?
    tod_left = (tod - (color_index/states))*states # what's the distance between the two
    for c, value in enumerate(color): # Go over last color's values (RGBA)
        difference = next_color[c]-value   # the difference between this color value and the next color value
        color[c] += difference*tod_left # multiply the difference between the distance, and add to the last color
    return tuple(color)


@Component()
class DayNightCycle:
    lights_node: NodePath = field(default_factory=lambda: NodePath("Day/Night Cycle Lights"))
    sun: DirectionalLight = field(default_factory=lambda: DirectionalLight("sun"))
    moon: DirectionalLight = field(default_factory=lambda: DirectionalLight("moon"))
    sun_colors: list = field(default_factory= lambda: list((
        (0.3, 0.0, 0.2, 0.0), # Night
        (0.6, 0.2, 0.0, 0.5), # Dawn
        (0.6, 0.4, 0.2, 1.0), # Afternoon
        (1.0, 0.0, 0.4, 0.5), # Evening
    )))
    moon_colors: list = field(default_factory=lambda: list((
        (0.1, 0.0, 0.4, 0.1), # Night
        (0.1, 0.1, 0.2, 0.2), # Dawn
        (0.1, 0.0, 0.1, 0.1), # Afternoon
        (0.6, 0.2, 0.2, 0.3), # Evening
    )))
    time_of_day: float = 0.5 # time of day


class CycleDayNight(System):
    entity_filters = {
        'daynightcycle': and_filter([
            Scene,
            Model,
            Calendar,
            DayNightCycle,
        ]),
    }

    def init_entity(self, filter_name, entity):
        model = entity[Model]
        cycle = entity[DayNightCycle]
        # Init begin of dawn
        cycle.sun.set_color(cycle.sun_colors[0])
        sunnp = cycle.lights_node.attach_new_node(cycle.sun)
        cycle.moon.set_color(cycle.moon_colors[0])
        moonnp = cycle.lights_node.attach_new_node(cycle.moon)
        entity[Scene].node.set_light(sunnp)
        entity[Scene].node.set_light(moonnp)
        cycle.lights_node.reparent_to(entity[Scene].node)

    def time_of_day_from_calendar(self, calendar):
        timeframes = list(calendar.timeframes.keys())
        timeframes.reverse()
        timeframe_sizes = []
        time_of_day = 0
        for timeframe in timeframes:
            if timeframe == calendar.cycle or len(timeframe_sizes) > 0:
                maxes.append(calendar.timeframes[timeframe][1])
                time = calendar.timeframes[timeframe][0]
                for timeframe_size in timeframe_sizes:
                    time /= timeframe_size
                time_of_day += time
        return time_of_day

    def update(self, entities_by_filter):
        for entity in entities_by_filter['daynightcycle']:
            cycle = entity[DayNightCycle]
            # get time_of_day as a float between 0 and 1
            if Calendar in entity:
                time_of_day = time_of_day_from_calender(entity[Calendar])
            else:
                time_of_day = cycle.time_of_day

            cycle.lights_node.getChild(0).set_p(90+(time_of_day*360))
            cycle.lights_node.getChild(1).set_p((-90+(time_of_day*360)))
            # set color according to time_of_day
            cycle.sun.set_color(tod_color(time_of_day, cycle.sun_colors))
            cycle.moon.set_color(tod_color(time_of_day, cycle.moon_colors))
