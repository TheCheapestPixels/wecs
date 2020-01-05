# WECS

WECS stands for World, Entities, Components, Systems, and is an implementation
of an ECS system. Its goal is to put usability first, and not let performance
optimizations compromise it.

Beyond the core, WECS' goal is to accumulate enough game mechanics, so that the
time between imagining a game and getting to the point where you actually work
on your specific game mechanics is a matter of a few minutes of setting up
boilerplate code. In particular, a module for Panda3D is provided.

## In WECS.

* A 'World' holds 'Entities' and 'Systems'.
* 'Entities' are made up of 'Components'.
* 'Components' contain an entity's data/variables.
* 'Systems' then 'filter' all the world's entities by their components, iterates over them and applies logic to component data.

This keeps data and logic seperated, modular, readable and reusable.

Optionally there are 'Aspects',
These are sets of components meant to be reinstanciated as new entities.

## Install
```
  pip install wecs
```

## Documentation

We're currently working on documentation. You can see it here: https://wecs.readthedocs.io/en/sphinx-start/

## A Hello World

```
from wecs.core import World, Component, System, and_filter


# Component that describes an entity that prints something
@Component()
class Printer:
    message: str


class Print(System):
    # Filter all entities in the world described as Printer
    entity_filters = {
        'printers' : and_filter([Printer])
    }

    def update(self, entities_by_filter):
        # Iterate over all filtered entities
        for entity in entities_by_filter['printers']:
            # Print their message
            print(entity[Printer].message)


world = World() # Make a world
world.add_system(Print(), 0) # Add to it the print system

printer_entity = world.create_entity() # A new entity
# Make it a Printer, and set it's message.
printer_entity.add_component(Printer(message="Hello World"))
world.update() # Run all added systems
```


## WECS for Panda3D
There are some game mechanics for panda3d that come out of the box:

* Camera modes:
    * First-person
    * Third-person
    * Turntable

* Character controller:
    * Flying/Floating
    * Crouching, Walking, Running, Sprinting and Strafing
    * Bumping, Falling and Jumping
    * Basic NPC movement
    * Stamina

<<<<<<< HEAD
* Animation:
    * Blended animations
    * Basic character controller animation
=======
* Bugs
  * CharacterController:
    * Bumping: Go into an edge. You will find yourself sticking to it
      instead of gliding off to one side.
    * Bumping: Go through a thin wall.
    * Bumping: Walk into a wall at a near-perpendicular angle, drifting
      towards a corner. When the corner is reached, the character will
      take a sudden side step. Easy to see when walking into a tree.
      Probably the result not taking inertia into account.
    * Falling: Stand on a mountain ridge. You will jitter up and down.
    * example: Break Map / LoadMapsAndActors out of game.py
  * CollideCamerasWithTerrain
    * With the head stuck against a wall (e.g. in the tunnel), this places
      the camera into the wall, allowing to see through it.
    * If the angle camera-wall and camera-character is small, the wall
      gets culled, probably due to the near plane being in the wall.
    * Changes in camera distance after startup do not get respected.
* Tests
  * Tests for `get_component_dependencies()` / `get_system_component_dependencies()`
  * Is there proper component cleanup when an entity is removed?
  * Does removing entities affect the currently running system?
  * Coverage is... lacking.
* Documentation
  * Well, docstrings!
  * Sphinx
  * doctests
* Development pipeline
  * tox
* core
  * API improvements
    * `entity = world[entity_uid]`
    * `entity = other_entity.get_component(Reference).uid`
  * Unique `Components`; Only one per type in the world at any given time, to
    be tested between removing old and adding new components?
  * De-/serialize world state
* boilerplate
  * Dump `Aspect`s into graphviz
* graphviz
  * Inheritance diagrams of `Aspect`s
* panda3d
  * character
    * Bumpers bumping against each other, distributing the push between them.
    * climbing
  * ai
    * Turn towards entity
    * Move towards entity
    * Perceive entity
  * Debug console
* mechanics
  * Meter systems: i.e. Health, Mana
* ai
  * Hierarchical Finite State Machine
  * Behavior Trees
  * GOAP / STRIPS
* All code
  * Change `filtered_entities` to `entities_by_filter`
  * `system.destroy_entity()` now gets `components_by_type` argument.
  * `system.destroy_entity()` is a horrible name. Change to `destroy_components`.
  * `system.init_entity()` is also misleading. Maybe change it to
    `system.init_components()`, and give it a `components_by_type` argument too?
  * I've been really bad about implementing `system.destroy_entity()`s...
  * `clock.timestep` is deprecated. Replace with `.wall_time`, `.frame_time`, or
    `.game_time`.
* examples: Minimalistic implementations of different genres, acting as guideposts for
  system / component development.
  * Walking simulator
    * documents / audio logs
    * triggering changes in the world
  * Platformer
    * 2D or 3D? Make sure that it doesn't matter.
    * Minimal NPC AI
  * Twin stick shooter
    * Tactical NPC AI
  * Creed-like climber
  * Stealth game
  * First-person shooter: "Five Minutes of Violence"
  * Driving game: "Friction: Zero"
  * Abstract puzzle game: "sixxis"
    * Candidate for list culling: Probably provides no reusable mechanics
  * Match 3
  * Rhythm game
    * Candidate for list culling: Just a specific subgenre of abstract puzzle games.
      Then again, it is a specific mechanic that defines a (sub)genre...
  * Environmental puzzle game
  * Turn-based strategy
    * Strategic AI
  * Real-time strategy
    * Strategic AI
  * Point and click
  * Role-playing game
    * Character sheet and randomized skill tests
    * Talking
  * Adventure
  * Flight simulator
  * City / tycoon / business / farming / life simulation
  * Rail shooter / Shooting gallery
  * Brawler
  * Bullet Hell
  * Submarine simulator
>>>>>>> 2129c8095e8fe1bdea38762e393ef637438c9655
