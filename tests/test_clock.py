import pytest

from wecs.mechanics import Clock
from wecs.mechanics import SettableClock
from wecs.mechanics import DetermineTimestep

from fixtures import world, entity


def test_basic_clock(world):
    world.add_system(DetermineTimestep(), sort=0)
    dt = 0.01
    clock = SettableClock(dt)
    entity = world.create_entity(Clock(clock=clock))
    world._flush_component_updates()
    
    assert dt < entity[Clock].max_timestep

    world.update()
    assert entity[Clock].timestep == dt


@pytest.fixture
def clock(world, entity):
    dt = 0.01
    clock = SettableClock(dt)
    entity[Clock] = Clock(clock=clock)
    world._flush_component_updates()
    assert dt < entity[Clock].max_timestep
    return clock


def test_clock_max_timestep(world, entity, clock):
    world.add_system(DetermineTimestep(), sort=0)
    dt = 0.1
    assert dt > entity[Clock].max_timestep
    clock.set(dt)

    world.update()
    assert entity[Clock].timestep == entity[Clock].max_timestep


def test_clock_scaling(world, entity, clock):
    world.add_system(DetermineTimestep(), sort=0)
    dt = 0.01
    factor = 0.5
    clock.set(dt)
    entity[Clock].scaling_factor = factor

    world.update()
    assert entity[Clock].game_time == dt * factor


def test_clock_cascade(world, entity, clock):
    world.add_system(DetermineTimestep(), sort=0)
    dt = 0.01
    clock.set(dt)

    # Child clock
    factor = 0.5
    child = world.create_entity(
        Clock(
            parent=entity._uid,
            scaling_factor=factor,
        ),
    )
    
    world.update()
    assert child[Clock].frame_time == dt
    assert child[Clock].game_time == dt * factor
