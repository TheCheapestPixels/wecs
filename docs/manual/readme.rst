What is WECS?
-------------

*WECS* stands for World, Entities, Components, Systems. It implements
the architecture pattern known as [ECS, EC, Component system (and
probably by several other names as well)]
(https://en.wikipedia.org/wiki/Entity_component_system), which is
popular in game development.

WECS aims at putting usability first, and to not let performance
optimizations compromise it.

Beyond the core which implements the ECS, the goal of WECS is to
accumulate enough game mechanics and boilerplate code so that the time
between imagining a game and getting to the point where you actually
work on your specific game mechanics is down to a few minutes.

In particular, systems and components to work with the `Panda3D
engine <https://www.panda3d.org/>`__ are provided.

Installation, etc.
------------------

-  Installation: ``pip install wecs``
-  Documentation:
   `readthedocs.io <https://wecs.readthedocs.io/en/latest/>`__
-  Source code: `GitHub
   repository <https://github.com/TheCheapestPixels/wecs>`__
-  Chat: `Panda3D Offtopic Discord server <>`__, channel
   ```#wecs`` <https://discord.com/channels/722508679118848012/722510686474731651>`__

Hello World
-----------

.. code:: python

   from wecs.core import *

   world = World()

A world contains ``Entities``; Also ``Systems``, more about those later.

::

   entity = world.create_entity()

``Entities`` themselves contain ``Components``; They are also nothing
more than a container for components. They are a general form of “game
object”, and can be turned into more specific objects by adding
``Components`` to them.

``Components`` are data structures with no inherent functionality (i.e.
they have no functions). Their presence on an entity describes the state
of an aspect of that entity. For example, a certain game object could be
the player’s car, having a ``Geometry`` component with its graphical
model, a ``Car`` component describing things like motor power and fuel
in the tank, a ``PhysicsBody`` keeping track of the car’s representation
in the physics simulation, and many more. Or it could be something as
simple as “An entity with this component can count”, or “It can print
its count (if it has one)”:

::

   @Component()
   class Counter:
       count: int = 0

   @Component()
   class Printer:
       name: str = "Bob"

   entity.add_component(Counter())
   entity.add_component(Printer())

During each ``world.update()``, the ``World`` will go through its list
of ``Systems``, and run each in turn. Each ``System`` has a list of
``Filters`` which test whether ``System`` should process an entity, and
in what kind of role.

::

   class CountAndPrint(System):
       entity_filters = {
           'count': Counter,
           'print': and_filter(Counter, Printer),
       }

       def update(self, entities_by_filter):
       for entity in entities_by_filter['count']:
           entity[Counter].count += 1
       for entity in entities_by_filter['print']:
           msg = "{} has counted to {}.".format(
           entity[Printer].name,
           entity[Counter].count,
       )
       print(msg)

   world.add_system(CountAndPrint(), 0)

The ``0`` in ``world.add_system(CountAndPrint(), 0)`` is the ``sort`` of
the system. Systems are run in ascending order of sort. As an aside,
it’d be a good idea to break this into two systems; Who knows what else
other people want to happen between counting and printing?

Now we can step time forward in this little universe:

::

   world.update()
   Bob has counted to 1.

This concludes the Hello World example.
