# WECS

WECS stands for World, Entities, Components, Systems, and is an implementation
of an ECS system. Its goal is to put usability first, and not let performance
optimizations compromise it.

Beyond the core, WECS' goal is to accumulate enough game mechanics so that the
time between imagining a game and getting to the point where you actually work
on your specific game mechanics is a matter of a few minutes of setting up
boilerplate code. In particular, a module for Panda3D is provided.


## WECS Fundamentals

* A `World` holds `Entities` and `Systems`.
* `Entities` are made up of `Components`.
* `Components` contain an `Entity`'s data / variables / state.
* `Systems` then `filter` all the world's `Entities` by their `Components`,
  iterate over them, and apply logic to `Component` data.

This has certain advantages over classic object-oriented programming:
* Data and logic separated, modular, readable and reusable.
* Compositional inheritance becomes the norm. One doesn't use inheritance
  to build a tree of classes, each more specialized then the last, but
  rather make combinations of small classes.
* Logic is applied only to entities that have the sets of `Components` that
  the logic works on. Thus they can be added and removed during an `Entity`'s
  life time, without tripping up the code workin on them.

There are also `Aspects`, which simplify adding and removing functionality
to and from `Entities`. An Aspect is a set of `Component` types, and the
default values for them. When an `Aspect` is added to an `Entity`, those
`Component`s are created and added to that `Entity`, and when the `Aspect`
is removed, so are its `Component` types.


## Installation
```
  pip install wecs
```


## Documentation

We're currently working on documentation. You can see it here: https://wecs.readthedocs.io/en/latest/


## How to use: A Hello World

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


## Boilerplate for Panda3D




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

* Animation:
    * Blended animations
    * Basic character controller animation

And a bunch more!
