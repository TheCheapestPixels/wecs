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


@Component()
class Clock:
    clock: FunctionType = None
    timestep: float = 0.0  # Deprecated
    max_timestep: float = 1.0/30
    scaling_factor: float = 1.0
    parent: UID = None
    wall_time: float = 0.0
    frame_time: float = 0.0
    game_time: float = 0.0


class DetermineTimestep(System):
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
