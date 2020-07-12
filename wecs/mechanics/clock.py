"""
A :class:`Clock` measures time for an entity. A typical use case is to
measure a frame's time in real-time applications, or advancing a 
simulation by specific time steps. Clocks provide a mechanism to clamp
time steps to a maximum (e.g. so as not to overwhelm a physics engine,
and allow it to regain real-time performance). They also provide a
mechanism to build a hierarchy of clocks, with children running at a
settable speed relative to their parent.
"""

from types import FunctionType
from collections import defaultdict

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import UID


class SettableClock:
    def __init__(self, dt=0.0):
        self.dt = dt

    def set(self, dt):
        self.dt = dt

    def __call__(self):
        return self.dt


def panda3d_clock():
    return globalClock.dt


@Component()
class Clock:
    """
    clock: A function that is called with no arguments and returns the
      elapsed time.
    timestep: Deprecated. Use wall_time, frame_time, or game_time
      instead.
    max_timestep: float = 1.0 / 30
    scaling_factor: Time dilation factor. This clock's game_time runs
      with a speed of `scaling_factor` relative to its parent.
      Default: 1.0
    parent: UID of the entity with the parent clock. `None` for root
      clocks.
    wall_time: The actual time delta. Set by :class:`DetermineTimestep`
    frame_time: The wall time, clamped to max_timestep.
    game_time: Frame time, scaled by scaling factor
    """
    clock: FunctionType = None
    timestep: float = 0.0  # Deprecated
    max_timestep: float = 1.0 / 30
    scaling_factor: float = 1.0
    parent: UID = None
    wall_time: float = 0.0
    frame_time: float = 0.0
    game_time: float = 0.0


class DetermineTimestep(System):
    """
    Update clocks. 
    """
    entity_filters = {
        'clock': and_filter([Clock]),
    }

    def update(self, entities_by_filter):
        clocks_by_parent = defaultdict(set)
        for entity in entities_by_filter['clock']:
            clocks_by_parent[entity[Clock].parent].add(entity)
        updated_parents = set()
        for entity in clocks_by_parent[None]:
            clock = entity[Clock]
            dt = clock.clock()
            # Wall time: The last frame's physical duration
            clock.wall_time = dt
            # Frame time: Wall time, capped to a maximum
            max_timestep = clock.max_timestep
            if dt > max_timestep:
                dt = max_timestep
            clock.frame_time = dt
            # FIXME: Provided for legacy purposes
            clock.timestep = dt
            # Game time: Time-dilated frame time
            clock.game_time = clock.frame_time * clock.scaling_factor
            # ...and to start the loop...
            updated_parents.add(entity._uid)
        while updated_parents:
            next_parents = set()
            for parent in updated_parents:
                if parent in clocks_by_parent:
                    for entity in clocks_by_parent[parent]:
                        child_clock = entity[Clock]
                        parent_clock = entity.world[parent][Clock]
                        child_clock.wall_time = parent_clock.wall_time
                        # FIXME: Rip out timestep
                        child_clock.timestep = parent_clock.frame_time
                        child_clock.frame_time = parent_clock.frame_time
                        child_clock.game_time = parent_clock.game_time * child_clock.scaling_factor
                        next_parents.add(entity._uid)
            updated_parents = next_parents
