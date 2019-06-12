# WECS

WECS stands for World, Entities, Components, Systems, and is an implementation
of an ECS system. For a detailed description, see the Design chapter below.


## Bob the Wizard

WECS comes with an example of a not-totally-trivial game in the form of a little
RPG.

Bob the Wizard is alive. Bob is aging. When Bob gets too old, his health will
deteriorate. If his health is gone, he dies. Bob knows a few spells. He knows
Rejuvenation and Restore Health, which make him younger and healthier, keeping
him alive, but they cost mana, which Bob gets only very slowly.

But there's something about Bob. Bob really doesn't want to die. Bob knows the
spell Lichdom, and one day, he may be able to cast it...


# Design

## ECS definition

* `Entities`
  * have a set of `Components`
  * are, with regard to how they are processed, typeless
* `Components`
  * are the state of an `Entity`
  * have a type
* `Systems`
  * have filters which have
    * a name identifying
    * a function testing for the presence of component types
  * process `Entities` when
    * a `Component` is added to the entity so that it now satisfies a filter.
      The System's `init_entity(filter_name, entity)` is called. This allows
      for setup, i.e. loading models into Panda3D's scene graph.
    * a `Component` is removed, so that the entity now does not satisfy a filter
      anymore. `destroy_component(filter_name, entity, component)` is called, .
      This allows for necessary breakdown. Do note that the component that has
      been removed is already not on the entity anymore, which is why it is
      passed as an extra argument.
    * the `System` is added to or removed from the `World`. This calls
      `init_entity()` or `destroy_entity()` respectively.
    * the `System`'s game logic is being run, caused by
      * `World.update()`
      * a task that is created when the `System` is added to the `World`
* `World`
  * has a set of `Entities`
  * has a set of `Systems`
  * causes `Systems` to process their relevant `Entities` in an appropriate
    running order


## User story: Need for AND- and OR-based component selection

There is a game with Bullet physics. To mitigate the effect of long frames, the
physics will cap the maximum timestep for a simulation step to 1/30 of a
second. This will slow down time in the simulation relative to a wall clock,
but solves the following issue:
Complex physics interactions can take a long time to process. When that happens
to delay the frame, using the increased frametime as the next timestep may cause
an even longer delay, causing the game to grind to a halt.
This is solved simply by capping the timestep. However, physics objects in the
game will have control logic being run on them that causes physics actions, like
i.e. a system processing thrusters applies an impulse to the rocket. These need
to scale to the timestep that will be used for the next physics simulation step.
Thus, there are two systems, `TimestepSystem` and `PhysicsSystem`, plus
game-specific system, here exemplified by `ThrusterSystem`.

* `TimestepSystem`
  * is run on `or_filter([PhysicsWorld, PhysicsObject])`, meaning entities with
    either component
  * gets the `PhysicsWorld` component (there is exactly one per world) and lets
    it determine (and store) the next timestep's length
  * stores the timestep on each `PhysicsObject` component
* `ThrusterSystem`
  * is run on `and_filter([Thruster, PhysicsObject])`, meaning the components of
    those types that are on any entity that has components of all of these
    types.
  * adds an impulse on each `PhysicsObject`, respecting the timestep field
* `PhysicsSystem`
  * is run on `and_filter([PhysicsWorld])`. Since only one component type is
    used here, it could just as well have been the `or_filter`, but the
    `and_filter` stops faster.
  * runs the physics simulation with the stored timestep


## Implementational detail: Optimizing type filtering performance

NOTE: I implemented prefiltering, but not quite like written down here.

As the number of Entities grows through expanding the game world or getting more
players, and the number of Systems grows due to new features in the game, the
complexity to filter the entities by a system's type list increases with O(m*n).
To prevent that from happening each frame, I propose to use mappings of
* A = {Entity: [Systems]}
* B = {System: [Components]}
that is modified when an Component or System is added or removed from or to the
World.

* Adding a Component to an Entity
  * Each System's type list is tested against the Entity's Components. If it
    matches, the System will from now on process this Component that is on this
    Entity (adding A and B mappings), and the System's init_components() will
    be called for the Component.
* Removing a Component from an Entity.
  * For each System from mapping A, we match its type list against the Entity.
    If it does not match anymore, we need to
    * remove the system from A
    * run the System's destroy_component() on he Component
    * remove the component from B
* Adding a System to the World
  * Its type list is tested against any Entity in the World. For each match,
    A and B mappings are added, and the System's init_components() is called
    with the matching Components.
* Removing a System from the World
  * All Components from B are used to determine the set of Entities that they
    are on, to remove the System from A.
  * On each Component from B, the System's destroy_component() is run
  * The System is removed from B.
* Running game logic
  * This step now requires merely one lookup per system in B to have the set of
    Components readily available.

There is an edge case where this approach runs into an issue with overselection.
Assume there's a system that processes the components of two sets of entities, X
and Y. It processes Y only if processing X has yielded a certain result. In
timesteps where that result does not come about, Y does not need to be
processed, thus not be filtered for in the first place.
In an "everything happens in RAM" situation, this is not a problem; references
to the Y set are available, whether they are needed or not, without any penalty
incurred. If the data is stored in a DB or over a network, however, the transfer
of data that makes it available to the system, however, should be avoided, since
this data transfer is a slow operation.

An upshot of eshewing dynamic querying for Components is that Systems have to be
upfront about what Component types they process, leading to a clear and
programmatically extractable understanding of System-Component dependencies.


## Components referencing each other

NOTE: This has been implemented using the "Unique values" approach described
below, with the references referring to `Entities`.

In a world, there is a thing, and it has the property of being a room:

    ```
    entity = world.create_entity()
    entity.add_property(Room())
    ```

In the world, there is another thing, and it's Bob:

    ```
    bob = world.create_entity()
    ```

Bob has the property of being in a room:

    ```
    bob.add_component(RoomPresence(room=...))
    ```

And at "..." the problem starts.


### Observer pattern

If I just use a reference

    ```
    RoomPresence(room=entity.get_component(Room))
    ```

that's bad, because there's no cleanup mechanism if `entity` gets removed from
the world. We could use the observer pattern to do that. Now `Room` has a list
of references, `observers`. RoomPresence(room=room) adds itself to that list.
When `entity.destroy()` is called, it destroys its components, calling
`Room.destroy()`, which calls all the `observers`. Thing is, now we experience
the problem in reverse. So `RoomPresence.destroy()` now must take care to clean
up the `observer` lists of all components that it is observing. You see how this
tends to get complicated?

On the upside, we now have a bus over which we can also send more general
events, though this will bring complications of its own. But like spells that
affect every affectable entity in the room could be implemented that way.

However, this upside is actually a downside. When we introduce inter-component
messaging, we now have components processing data, and have broken the
fundamental paradigm of ECS:

* Components are data
* Systems are processing
* System-System interaction should happen by manipulating data

So, what can we do instead?


### Unique values

If we use unique values

    ```
    room.add_component(Room(uid="Balcony"))
    bob.add_component(RoomPresence(room="Balcony"))
    ```

then we have I have to make sure that those UIDs are in fact unique. That isn't
too difficult:

    ```
    room.add_component(Room())
    bob.add_component(RoomPresence(room=room.get_component(Room)._uid))
    ```

The `Room._uid is generated automatically during `add_component()`, and then the
component is registered with the `World`. Now when a `System` `CastSpellOnRoom`
runs and sees that Bob does indeed cast a spell on the room that he is in, so it
tries

    ```
    room_uid = RoomPresence(room=room.get_component(Room)._uid
    room = world.get_component(_uid)
    ```

to do something with the room, but if the room has already been destroyed,
`world.get_component()` will raise a `KeyError("No such component")`. It's now
up to the system how to deal with that, and how to bring Bob's `RoomPresence`
component back into a consistent state.

However, it's not this system's *job* to clean up after `RoomPresences`, it is
to cast a spell. What it can do, or what should ideally happen automatically, is
that Bob gets marked as needing cleanup (e.g. `bob.add_component(CleanUpRoom)`),
and that a dedicated system deals with what consistency means in the game (e.g.
just removing the component, or setting the referenced room to an empty void for
the player to enjoy). This in turn leads to possible race conditions; *when*
does that transition happen during a frame? On the other hand, since *all*
systems that can't work properly anymore due to this inconsistent situation
should deal predictably and fail-safe (mark and proceed with other entities)
with it, this should be of preventable impact.


## Implementational detail: Size of GUIDs (TL;DR: 64 bit is the right answer)

NOTE: Theoretical for now, there are no GUIDs being used yet.

Entities act as nothing more than a label, and are usually implemented as a
simple integer as a globally unique identifier (GUID). The question arises: How
many of those do we need?

Assume a game of five million concurrent players, and a thousand Entities in the
game world per player. Thus we arrive at five billion Entities in the game
world. This is just above 2**32 numbers (4.29 billion). 64 bit offers over 18
quintillion IDs, which should be enough for even the largest player base with a
staggering amount of per-player content of the game world.


## Implementational detail: Systems threading

One advantage of ECSes seems to be parallelization. Systems can run in parallel
as they are independent of each other. I think that that's Snake Oil, and I
won't buy it that easily.

* There is time. The basic time unit of a game is usually a frame on the
  client's side, and a tick on the server side. A system may run as fast and as
  often as it pleases if all that is does is triggered by state changes on
  components, and thus effectively does event-driven processing on them.
  However, if that is not the case for a given system, then it will likely need
  to run once per frame/tick. Thus, a synchronization point between systems is
  needed.
* There are cause-and-effect dependencies. Consider input, physics, and
  rendering. In any given frame, these need to happen in a defined sequence, so
  that the player is presented with a consistent game state.
* There is no time. Every now and then, a System may need to perform a
  time-costly operation, like loading a model from disk or, even worse, over the
  network. This would bring the advantages of parallelity to the forefront, as
  only this specific system would stall, and all others would keep running and
  pick up on the results of the operation once it is available. This, however,
  can only happen if there are no synchronization points between those other
  systems and the stalling one.

I have no idea how to square these with each other elegantly, though within
Panda3D, the task manager can solve this. Long-running systems into separate
task chains to run asynchronous, while "every frame" tasks are put into the
default task chain.

CURRENT STATE: When a system is added, an `int` is provided. `world.update()`
will run the task in order of ascending numbers.


## Note: Component inheritance

One basic design feature of an ECS is the separation of data from the code that
processes it. One could now get the idea "Excellent, then I can have a class
hierarchy of Components, and the Systems will process those Components that
subclass their component types."
The perceived upshot here is that as gameplay is iterated on, Components can be
enriched with new functionality (implemented in Systems) that add to existing
behavior, while old behavior runs on unaltered for those components that are
still of the base component's type.
This is unnecessary and potentially dangerous. The alternative is to just add a
new component type, and a system that runs on entities where both components are
present. This leads to easy management of the system:
* Old items should be individually upgraded, or need to be upgraded for the new
  rollout? Just add the new component, no upgrade mechanism necessary.
* The feature wasn't fun after all? Remove the new Components from the game. No
  need to have a downgrade mechanism for components of the new type. Systems
  that fall into disuse can be identified automatically.
* You end up with two Systems anyway.
* If you're doing hierarchical inheritance on the component types, you incur the
  penalties outlined above. If you're doing compositional inheritance, you're
  just replicating what ECS does anyway when you add a new component type to an
  entity.


## Sources

* http://t-machine.org/index.php/2007/09/03/entity-systems-are-the-future-of-mmog-development-part-1/
* https://www.gamedevs.org/uploads/data-driven-game-object-system.pdf


# TODO

* Tests
  * Tests for `get_component_dependencies()` / `get_system_component_dependencies()`
  * Is there proper component cleanup when an entity is removed?
* core
  * API improvements
    * `entity = world[entity_uid]`
    * `entity = other_entity.get_component(Reference).uid`
    * `component = entity[Reference]`
  * Break adding/removing components out of `update()`, executing them after it
  * Unique `Components`
  * Archetypes: Make it easy to compose typical entities
* rpg
  * Hoist `Room` / `RoomPresence` into `wecs`, maybe some standard C/S file?
* panda3d-pong
  * Create custom models
  * Remove positioning hacks from `Model` after creating Pong models
  * Hoist `Components` / `Systems` into `panda3d.py` where applicable
* panda3d
  * Check the `task_mgr` for tasks already existing at a given sort
  * If that's not possible, `System`ify existing Panda3D `tasks`
