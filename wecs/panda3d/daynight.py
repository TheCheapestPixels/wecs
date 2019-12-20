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


def tod_color(tod, colors, index_offset=0):
    states = len(colors)-1 # How many colors to blend to/from
    color_index = (int(tod*states)+index_offset)%states # When was the last color?
    color = list(colors[color_index]) # What color is it?
    next_color = list(colors[(color_index+1)%states]) # what's the next color?
    tod_left = ((tod*states)-color_index)/states # where between the two colors are we?
    for c, value in enumerate(color): # Go over last color's values (RGBA)
        difference = next_color[c]-value   # the difference between this color value and the next color value
        print(color[c])
        color[c] += difference*tod_left # multiply the difference between the distance, and add to the last color
        print("col", color[c], "dif", difference)
    return tuple(color)


@Component()
class DayNightCycle:
    heaven: NodePath = field(default_factory=lambda: NodePath("heaven"))
    sun: DirectionalLight = field(default_factory=lambda: DirectionalLight("sun"))
    moon: DirectionalLight = field(default_factory=lambda: DirectionalLight("moon"))
    # sun_colors [(Sunrise), (Peak), (Sunset)]
    sun_colors: list = field(default_factory= lambda: list(
        ((1,0.2,0,0.5), (1,1,1,1), (1,0.1,0.5,0.5))
    ))
    # moon_colors [(Sunset), (Midnight), (Sunrise)]
    moon_colors: list = field(default_factory=lambda: list(
        ((0.2,0.5,0.5,0.5), (0.2,0.2,0.7,1), (0.2,0.5,0,0.5))
    ))


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
        sunnp.set_r(-90)
        cycle.moon.set_color(cycle.moon_colors[0])
        moonnp = cycle.heaven.attach_new_node(cycle.moon)
        moonnp.set_r(90)
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
            #print(tod)
            # set heaven node's roll to tod*360
            cycle.heaven.set_r(tod*360)
            # set color according to tod
            sun_colors = ((0,0,0,0),) + tuple(cycle.sun_colors) + ((0,0,0,0),)
            cycle.sun.set_color(tod_color(tod, sun_colors))
            moon_colors = ((0,0,0,0),) + tuple(cycle.moon_colors) + ((0,0,0,0),)
            cycle.moon.set_color(tod_color(tod, moon_colors, 3))
