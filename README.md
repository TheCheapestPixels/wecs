# WECS

WECS stands for World, Entities, Components, Systems, and is an implementation
of an ECS system.


## ECS definition

* `World`
  * has a set of `Entities`
  * has a set of `Systems`
  * causes `Systems` to process their relevant `Entities` in an appropriate
    running order
* `Entities`
  * have a set of `Components`
  * are, with regard to how they are processed, typeless
* `Components`
  * are the state of an `Entity`
  * have a type
* `Systems`
  * have filters which have
    * a name identifying them
    * a function testing for the presence of component types
  * process `Entities` when
    * a `Component` is added to the entity so that it now satisfies a filter.
      The System's `init_entity(filter_name, entity)` is called. This allows
      for setup, i.e. loading models into Panda3D's scene graph.
    * a `Component` is removed, so that the entity now does not satisfy a filter
      anymore. `destroy_entity(filter_name, entity, components_by_type)` is
      called. This allows for necessary breakdown. Do note that the components
      that have been removed are already not on the entity anymore, which is why
      they are passed as an extra argument.
    * the `System` is added to or removed from the `World`. This calls
      `init_entity()` or `destroy_entity()` respectively.
    * the `System`'s game logic is being run, caused by
      * `World.update()`
      * a task that is created when the `System` is added to the `World`


## API

NOTE: `wecs/examples/minimal/main.py` offers a more complete overview of the
API, including systems, but doesn't incorporate the syntactic sugar mentioned
below yet.

Create a world, an entity, a component, and tie it all together:
```
from wecs.core import World, Component


@Component()
class Foo:
  pass


world = World()
entity = world.create_entity()
foo_component = Foo()
entity.add_component(foo_component)
```

Entity creation can also take components to be added as arguments:
```
world.create_entity(Foo(), ...)
```

Getting and removing components, and checking for their presence:
```
is_present = entity.has_component(Foo)
foo_component = entity.get_component(Foo)
entity.remove_component(Foo)
```

A bit of syntactic sugar later:
```
entity[Foo] = foo_component
is_present = Foo in entity
foo_component = entity[Foo]
del entity[Foo]
```

The `Foo` in `entity[Foo] = foo_component` is something that doesn't have to be
given to `entity.add_component(foo_component)`, since its type is known. It's
needed here merely because `entity[] = foo_component` isn't syntactically valid
Python.


# Design

## Deferred `Component` addition / removal

Do note that additions / removals of components are deferred, and only take
effect once `world.flush_component_updates()` is called, which happens
automatically when (before) a `System` is being run. Thus you can let a `System`
process one entity, let that processing cause the removal of a component of
another entity, then let the `System` go on to do the same the other way
around, even if the system depends on the presence of the now "removed"
component. That way, when processing each `Entity`, the system is presented
with the state (of component presence) from when the system is started.

However, if you *add* components, on one hand, they won't e added to any
filter immediately, just like they won't be removed by dropping a component
(since those updates are deferred). But you *can* still access them through
`entity.has_component(ComponentType)` and
`entity.get_component(ComponentType)`, as those functions use the sets of both
existing and newly added components.

Do also note that none of this magic holds true for the values of state;
You're on your own in that regard. Splitting systems into "This can be done",
"This is being done", and "Now we're cleaning up weird states that could have
come about" seems to be a workable pattern.


# Design questions and arguments

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

CURRENT STATE: When a system is added, an `int` is provided. `world.update()`
will run the task in order of ascending numbers.

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


## Note: Component Inheritance Considered Dangerous

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


## Composing templates for generic entities

To set up entities individually, giving them their components and the starting
values of those, is repetitive and inefficient. Even writing a factory function
for each type of entity in your game is repetitive, because in all likelihood,
some kinds of entities will be very similar to each other.

Thus we need factory functions that create entities from sets of building
blocks, and allow for overriding the given default values on a per-entity basis.
The question is: How are those building blocks put together?

Two approaches offer themselves:
* Archetypes: Just use Python's inheritance system. Conflicts due to diamond
  inheritance should be resolved by the usual linearization rules. Frankly I
  have not thought too deeply about this approach.
  * Pros: People who know Python know how this works
  * Cons: Didn't we just get rid of OOP inheritance for reasons?
* Aspects: We'll do EC-like composition again on a higher level.
  * An aspect is a set of component types (and values diverging from the
    defaults) and parent aspects. When you create an entity from a set of
    aspects, all component types get pooled. Unlike to Archetypes, each type
    must be provided only once. This disallows diamond inheritance and forces a
    pure tree inheritance.
    * This can already be checked on aspect creation
    * It also allows for testing at runtime whether an entity still fulfills an
      archetype.
    * This in turn allows for removing and adding aspects at runtime while
      insuring that aspects lower down in the hierarchy still match. An entity
      can be given several different instances of an archetype, only one of
      which can be active at any given time, but can be swapped out for another
      one.
  * API draft:
    ```
    * Aspect(aspects_or_components, overrides=None)
      Creates an aspect.
      Calling an aspect returns a set of new component instances.
      `overrides` provides default values to use instead of the ones on the
      provided aspects.
      Calling an aspect with overrides does not invalidate, but possibly
      override, an aspect's overrides.

      moveset = [WalkingMovement, InertialMovement, BumpingMovement, FallingMovement]
      walker = Aspect(moveset)
      slider = Aspect(moveset, {InertialMovement: dict(acceleration=5.0)})
      world.create_entity(slider())  # A walker with acceleration of 5.0
      world.create_entity(slider({InertialMovement: dict(rotated_inertia=1.0)})))  # Acceleration is still 5.0
    * add_aspect(entity, components)
      Just a bit of syntactic sugar, and may perform a check whether component
      clashes would occur before adding any component.
    * MetaAspect(list_of_aspects)
      A MetaAspect is a list of aspects. Components can not be created from a
      MetaAspect. Its purpose is to serve as a flexible filter when removing
      aspects from an entity. Instead of of one aspect, it is given a list of
      them, which is matched in order against the entity. The first one to
      match is then removed from the entity.
    * remove_aspect(entity, aspect_or_metaaspect)
      Returns the set of removed components.
    ```
  * Use case:
    ```
    # For readability, default values are omitted, and the
    # The minimum that a character can be is a disembodied character...
    character = Aspect([Clock, Position, Scene, CharacterController])
    # ...until it gets a body.
    avatar = Aspect([character, Model, WalkingMovement, Stamina])
    spectator = Aspect([character, Model, FloatingMovement])

    # A player has a camera with which to see into the world.
    first_person = Aspect([FirstPersonCamera])
    third_person = Aspect([ThirdPersonCamera])
    camera = MetaAspect([first_person, third_person])

    # Most characters have logic that controls their actions.
    input = Aspect([Input])
    ai = Aspect([ConstantCharacterAI])
    control = MetaAspect([input, ai])

    # To make our lives easier, a high-level abstractions...
    # (This is the one case that makes MetaAspects necessary.)
    mind = MetaAspect([Aspect([control, camera]), control])
    # ...and templates.
    player_character = Aspect([avatar, input, first_person])
    non_player_character = Aspect([avatar, ai])

    # Now let's create some entities!
    player_entity = world.create_entity(player_character())
    npc_entity = world.create_entity(npc_character())

    # What if "minds" that control characters could swap bodies?
    def swap_minds(entity_a, entity_b):
        mind_a = remove_aspect(entity_a, mind)
        mind_b = remove_aspect(entity_b, mind)
        add_aspect(entity_a, mind_b)
        add_aspect(entity_b, mind_a)
    swap_minds(player_entity, npc_entity) # This will get confusing...
    swap_minds(player_entity, npc_entity) # Much better.

    # Now let's force a 3rd Person camera on the player.
    remove_aspect(npc_entity, camera)
    add_aspect(npc_entity, third_person())
    ```
  * Pros:
    * Looks like it might work; Further research is warranted.
  * Cons:
    * Does this actually reduce complexity?
    * What kind of type-theoretical implications does it have?


## Sources

* http://t-machine.org/index.php/2007/09/03/entity-systems-are-the-future-of-mmog-development-part-1/
* https://www.gamedevs.org/uploads/data-driven-game-object-system.pdf


# TODO

## Hot Topics

* panda3d
  * Finish boilerplaterization of panda3d-character-controller/main.py
  * Check the `task_mgr` for tasks already existing at a given sort
  * If that's not possible, `System`ify existing Panda3D `tasks`
  * character.Walking
    * Decreased control while in the air
    * Null input should have zero effect, not effect towards zero movement
  * character.Jumping
    * Multijump


## Icebox

* Update PyPI package
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
  * CollideCamerasWithTerrain
    * With the head stuck against a wall (e.g. in the tunnel), this places
      the camera into the wall, allowing to see through it.
    * If the angle camera-wall and camera-character is small, the wall
      gets culled, probably due to the near plane being in the wall.
* Tests
  * Tests for `get_component_dependencies()` / `get_system_component_dependencies()`
  * Is there proper component cleanup when an entity is removed?
  * Does removing entities affect the currently running system?
  * Coverage is... lacking.
* core
  * API improvements
    * `entity = world[entity_uid]`
    * `entity = other_entity.get_component(Reference).uid`
  * Unique `Components`; Only one per type in the world at any given time, to
    be tested between removing old and adding new components?
  * De-/serialize world state
* graphviz:Inheritance diagrams of `Aspect`s
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
  * GOAP / STRIPS
* examples
  * Minimalistic implementations of different genres, acting as guideposts for
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
* All code
  * Change `filtered_entities` to `entities_by_filter`
  * `system.destroy_entity()` now gets `components_by_type` argument.
  * `system.destroy_entity()` is a horrible name. Change to `destroy_components`.
  * `system.init_entity()` is also misleading. Maybe change it to
    `system.init_components()`, and give it a `components_by_type` argument too?
  * I've been really bad about implementing `system.destroy_entity()`s...
