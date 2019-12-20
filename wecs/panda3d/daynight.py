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
    heaven: NodePath = field(default_factory=lambda: NodePath("heaven"))
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
        sunnp = cycle.heaven.attach_new_node(cycle.sun)
        cycle.moon.set_color(cycle.moon_colors[0])
        moonnp = cycle.heaven.attach_new_node(cycle.moon)
        model.node.set_light(sunnp)
        model.node.set_light(moonnp)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['daynightcycle']:
            calendar = entity[Calendar]
            cycle = entity[DayNightCycle]
            # get time of day (tod) from calender as float between 0 and 1
            # this many decimals is probably imprecise,
            # in which case multiply all timeframes before dividing
            #print(calendar)
            tod = (calendar.hour[0]/calendar.hour[1])
            tod += (calendar.minute[0]/calendar.minute[1])/calendar.hour[1]
            tod += ((calendar.second[0]/calendar.second[1])/calendar.minute[1])/calendar.hour[1]
            cycle.heaven.getChild(0).set_p(90+(tod*360))
            cycle.heaven.getChild(1).set_p((-90+(tod*360)))
            # set color according to tod
            cycle.sun.set_color(tod_color(tod, cycle.sun_colors))
            cycle.moon.set_color(tod_color(tod, cycle.moon_colors))
