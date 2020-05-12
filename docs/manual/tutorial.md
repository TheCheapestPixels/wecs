Tutorial
========

What is an ECS?
---------------

ECS is an architecture aimed at simplifying the development and
maintenance of complex video games. Ideas that have shaped WECS are
that...
* state should be separated from the logic working on it,
* state objects (often also called 'game objects' for lack of a better
  term) should be extended by using composition instead of classical
  patterns of inheritance, and be extendable and restrictable at
  runtime,
* logic is applied in a round-robin fashion; In the context of games
  that likely means "each piece of logic is applied once per frame, in a
  predetermined order",
* logic processes those objects to which it is applicable, determined by
  their current type,
* different parts of logic communicate with each other via the state
  changes that they cause.

In the context of ECS, state objects are called `Entities`, and
critically, *they do not by themselves store any actual state*. Instead,
they are collections for `Components`, which contain the state. An
`Entity` without `Components` is a game object with no state, and thus
no logic is working on it.

`Components` have a type, and contain fields of data. They closely
correspond to Python dataclasses. They offer no functionality, just pure
state.

Pieces of logic are called `Systems`. Each `System` has `Filters`, which
are simple pattern matching functions that test whether an `Entity`
should be processed by the `System`, and how, based on what types of
`Components` the `Entity` has. (Note that the idea of there being
*multiple* `Filters` per `System` seems so far to be specific to WECS.)

The `World` is the container for `Entities` and `Systems`. It provides
funtionality to advance the state one time step by running all `Systems`
in order.

FIXME: We really need a graphic here, or at least some table.


World
-----

```python
from wecs.core import World
world = World()
world.update()
```

If you're using the Panda3D boilerplate, a `World` will be provided as
`base.ecs_world`. There's no need to call `.update()`, as `Systems` get
wrapped into tasks.


Components
----------

Components are no more complicated than shown in the Hello World
example. Consider them dataclasses; Under the hood, they (currently)
are.

```python
from wecs.core import Component

@Component()
class MyComponent:
    pass
```


Entities
--------

```python
# Creating / destroying entities                
entity = world.create_entity()     # Creating an entity
entity = world.create_entity(      # Add components during creation
    ComponentA(),
    ComponentB(),
)
world.destroy_entity(entity)       # Destroy entity

# Working with components
entity[Component] = Component()    # Add component
component = entity[Component]      # Get component
Component in entity                # Check for presence
del entity[Component]              # Remove component
```

The actions of adding and removing `Components` to and from `Entities`
is deferred; That is, it is not being executed at the time that it is
commanded. While rarely relevant, it should be kept in mind. Details on
it can be found below under `Systems` (FIXME: Link to section). The only
thing necessary to keep in mind for now: Component additions and
removals do not happen immediately.

Deferral happens so that you can manipulate `Entities` within a
`System`'s `update()` function, but maintain its set of components for
other code in that function which may expect it to be in the state that
it was in when the `update()` began. For example, removing a `Component`
immediately may lead to a state where it does not satisfy a `Filter`
anymore, but since it was in it when the update began, it will still be
processed later on in the `update()`. By deferring the removal, simpler
and less bug-prone code can be written.

Deferred updates are executed ("flushed") by calling
`world._flush_component_updates()`. It is rarely necessary to do that
flush yourself; It is automatically done before each `System.update()`,
and also each `world.add_system()`. The only case where it is useful is
when you have code external to WECS (other than initial setup) that
manipulates an `Entity`'s component set, *and* then has other code that
tries to access the `Entity` in its new state. If you ever come across
such a use case, a "Why not just make those `Systems`?" may be in order.


References
----------

FIXME: UID


Systems
-------

```python
from wecs.core import System
from wecs.core import and_filter, or_filter


class MySystem(System):
    entity_filters = {
        'just_a': ComponentA,
	'complex': and_filter(
            ComponentA,
	    or_filter(ComponentB, ComponentC),
	)
    }

    def enter_filter_just_a(self, entity):
        pass

    def exit_filter_just_a(self, entity):
        pass

    def enter_filter_complex(self, entity):
        pass

    def exit_filter_complex(self, entity):
        pass

    def update(self, entities_by_filter):
        # We'll get something like:
	# {'just_a': set(entity_1, entity_2),
	#  'complex': set(entity_1),
	# }
	pass
```

FIXME: Explanation
FIXME: Details on deferred flushes


Summary: WECS core
------------------

* `World`
  * has a set of `Entities`
  * has a set of `Systems`
  * causes `Systems` to process their relevant `Entities` in an
    appropriate running order
* `Entities`
  * have a set of `Components`
  * are, with regard to how they are processed, type- and stateless
* `Components`
  * are the state of an `Entity`
  * have a type
* `Systems`
  * have filters which have
    * a name identifying them
    * a function testing for the presence of component types
  * process `Entities` when
    * `Components` are added to the `Entity` so that it now satisfies
      a filter; `System.enter_filter_<filter_name>(entity)` is called
      with the `Entity`'s post-addition state,
    * `Components` are removed from the `Entity` so that it now does
      not satisfy a filter anymore;
      `System.exit_filter_<filter_name>(entity)` with the `Entity`'s
      post-removal state,
    * the `System` is added to or removed from the `World`; It will call
      `enter/exit_filter_<filter_name>` accordingly,
    * `System.update`, its recurring game logic, is being run, caused by
      `world.update()`.

A game is set up by...
* creating `Entities` in the `World`, and giving them the `Components`
  that describe their properties,
* adding a list of `Systems` which describe how components’ states
  should change over time; This is the content of your main loop.

Now when running the main loop, each `System` will fetch all `Entities`
that have sufficient `Components` to satisfy one or more of its filters,
then update them. This may involve updating `Components` that aren’t on
any of the `System`'s filters, and which may even be on any `Entity` in
the `World`.


Aspects
-------

FIXME: Code

`Aspects` simplify adding and removing groups of `Components` to and
from `Entities` to and from `Entities`. An Aspect is a set of
`Component` types, and the default values for them. When an `Aspect` is
added to an `Entity`, those `Component`s are created and added to that
`Entity`, and when the `Aspect` is removed, so are its `Component`
types.
