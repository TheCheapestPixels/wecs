Design Notes
============

Warning
-------

This part of the documentation is where I store my ramblings about ECS
design for future reference.


Why ECS?
--------

Structuring things like this has certain advantages over classic
object-oriented programming:
* Data and logic are separated, modular, readable and reusable.
  Admittedly, that is also the sales pitch of OOP itself. ECS is a
  further measure in controlling the mess that is game development.
* Compositional inheritance becomes the norm. One doesn't use
  inheritance to build a tree of classes, each more specialized then
  the last. Instead, a game object can be said to have a type based on
  what components it has at any given time.
* `Systems` work only on entities that have sets of `Components` that
  the `System` works on. Thus they can be added and removed during an
  `Entity`'s life time, without tripping up the code working on them.
* In games, time is occurring in discrete steps anyway, inspiring the
  round-robin nature of `Systems`.
* `Systems` are insulated from one another unless they work on the same
  component types. If they do, they need to agree with all other
  `Systems` on the semantics of the fields of that `Component`. As long
  as they do that, `Systems` can be developed with very little danger of
  side effects.
* Being mostly safe from side effects allows to add and remove new
  systems at low development cost and technical debt, which in turn
  allows for free experimentation and organic development during both
  initial development and long product lifetimes. At its extreme, game
  mechanics can be added and removed at runtime, making downtime in
  persistent multiplayer servers obsolete.
* A well-insulated game mechanic is also transferrable between many
  games, cutting down development time, especially during prototyping.


Deferred Component addition / removal
-------------------------------------

### Motivation

Imagine that you have a shooter game where two characters each have a
gun that removes the gun that removes the gun of the target. At the
same moment, those characters shoot at each other.

For some reason that is realized by removing the target's `Gun`
component; Good software design is secondary here, I want to make a
point about how to work with components. Then there is a
system `Shoot` that resolves the shots. Its filter applies
to all entities with a `Gun` component.

When `Shoot`'s `update()` runs, it iterates over the first
entity in its filter, then the second. The order can be
considered random and should not matter.

When it processes the first entity, it looks up its `Gun`, sees the
shot, finds the target (the second entity), removes its `Gun`, and
is done.

When it processes the second entity, it looks up its `Gun`, and an
`Exception` would be thrown at this point, since the entity does not
have that component anymore. It should not even be in the filter
anymore. But that's just bad semantics that shouldn't be fixed by
hackin around the problem. The "true" semantics is that a system
is given a state of aspects of the world, and should transform that
into its successor state, and do so in as small, compact, and easy to
reason over units; It should not make the developer deal with
intermediate states. It has turned out that simply iterating over all
entities in a filter is *the* building block of `update()`. During
no iteration should the developer have to think about what happened in
any other iteration. The entity should be presented to the code within
the loop as it was at the beginning of the iteration in all aspects
that are read from it.

Luckily, there is a solution... -ish thing.


### Deferring changes

When we add or remove components, we do not process those changes
while the system is running. Instead, we simply treat these actions as
requests that we queue up an will process at a later time. A good time
for that is "any time right before a system is updated", since it
cleans up any dirty state, like the setup of a specific world's state
in the beginning leaves. Another good time is right after a system,
since a developer may choose to let code outside of `System`s
interact with the `World`'s state, so it'd be helpful to leave a
clean state. And since cleaning up a clean state is close to a null
operation, there is no downside to doing both.

When deferring component updates, it is necessary to define the
semantics of getting and setting components well. After some
experimentation with "more intelligent" I'll be returning to "more
simple" for v0.2. "More intelligent" mostly just breeds complexity, and
is designed for edge cases that may never happen.

So, additions / removals of components are deferred, and only
take effect once `world._flush_component_updates()` is called, which
happens automatically when (before) a `System` is being run. Thus you
can let a `System` process one entity, let that processing cause the
removal of a component of another entity, then let the `System` go on
to do the same the other way around, even if the system depends on the
presence of the now “removed” component. That way, when processing each
`Entity`, the system is presented with the state (of component
presence) from when the system is started.

However, if you *add* components, on one hand, they won’t be added to
any filter immediately, just like they won’t be removed by dropping a
component (since those updates are deferred). But you *can* still access
them through `ComponentType in entity` and `entity[ComponentType]`,
as those functions use the sets of both existing and newly added
components. NOTE: Not in v0.2 anymore. Needing to access those is that
unlikely-to-occur edge case.

Do also note that none of this magic holds true for the values of state;
You’re on your own in that regard. If a `System` processes an
`Entity` and changes some state, then processes another `Entity`,
that process will not see the original state, only the current state.

Splitting systems into "This can be done", "This is being done", and
"Now we’re cleaning up weird states that could have come about" seems to
be a workable pattern.


Implementational detail: Optimizing type filtering performance
--------------------------------------------------------------

NOTE: I've ended up implementing it simpler, but the end result is still
that each `System` maintains a mapping of `{Filter: set(Entity)}`. When
an `Entity` is changed, it will be tested against all `Filters`. While
this could be optimized further (by testing only against filters that
test for the changed components), it is already a rather lightweight
operation and unlikely to be a game's bottleneck.


As the number of Entities grows through expanding the game world or
getting more players, and the number of Systems grows due to new
features in the game, the complexity to filter the entities by a
system’s type list increases with O(m\ *n). To prevent that from
happening each frame, I propose to use mappings of* A = {Entity:
[Systems]} \* B = {System: [Components]} that is modified when an
Component or System is added or removed from or to the World.

* Adding a Component to an Entity
  * Each System’s type list is tested against the Entity’s Components.
    If it matches, the System will from now on process this Component
    that is on this Entity (adding A and B mappings), and the System’s
    init_components() will be called for the Component.
* Removing a Component from an Entity.
  * For each System from mapping A, we match its type list against the
    Entity. If it does not match anymore, we need to
    * remove the system from A
    * run the System’s destroy_component() on he Component
    * remove the component from B
* Adding a System to the World
  * Its type list is tested against any Entity in the World. For each
    match, A and B mappings are added, and the System’s
    init_components() is called with the matching Components.
* Removing a System from the World
  * All Components from B are used to determine the set of Entities
    that they are on, to remove the System from A.
  * On each Component from B, the System’s destroy_component() is run
  * The System is removed from B.
* Running game logic
  * This step now requires merely one lookup per system in B to have
    the set of Components readily available.

There is an edge case where this approach runs into an issue with
overselection. Assume there’s a system that processes the components of
two sets of entities, X and Y. It processes Y only if processing X has
yielded a certain result. In timesteps where that result does not come
about, Y does not need to be processed, thus not be filtered for in the
first place. In an "everything happens in RAM" situation, this is not a
problem; references to the Y set are available, whether they are needed
or not, without any penalty incurred. If the data is stored in a DB or
over a network, however, the transfer of data that makes it available to
the system, however, should be avoided, since this data transfer is a
slow operation.

An upshot of eshewing dynamic querying for Components is that Systems
have to be upfront about what Component types they process, leading to a
clear and programmatically extractable understanding of System-Component
dependencies.


Components referencing each other
---------------------------------

NOTE: This has been implemented using the "Unique values" approach
described below, with the references referring to `Entities`. The
confusing use of API probably stems from the original design phase of
WECS.

In a world, there is a thing, and it has the property of being a room:

```python
entity = world.create_entity()
entity.add_property(Room())
```

In the world, there is another thing, and it’s Bob:

```python
bob = world.create_entity()
```

Bob has the property of being in a room:

```python
bob.add_component(RoomPresence(room=...))
```

And at “...” the problem starts.


###Observer pattern


If I just use a reference

```python
RoomPresence(room=entity.get_component(Room))
```

that’s bad, because there’s no cleanup mechanism if `entity` gets
removed from the world. We could use the observer pattern to do that.
Now `Room` has a list of references, `observers`.
RoomPresence(room=room) adds itself to that list. When
`entity.destroy()` is called, it destroys its components, calling
`Room.destroy()`, which calls all the `observers`. Thing is, now we
experience the problem in reverse. So `RoomPresence.destroy()` now
must take care to clean up the `observer` lists of all components that
it is observing. You see how this tends to get complicated?

On the upside, we now have a bus over which we can also send more
general events, though this will bring complications of its own. But
like spells that affect every affectable entity in the room could be
implemented that way.

However, this upside is actually a downside. When we introduce
inter-component messaging, we now have components processing data, and
have broken the fundamental paradigm of ECS:

* Components are data
* Systems are processing
* System-System interaction should happen by manipulating data

So, what can we do instead?


###Unique values

If we use unique values

```python
room.add_component(Room(uid="Balcony"))
bob.add_component(RoomPresence(room="Balcony"))
```

then we have I have to make sure that those UIDs are in fact unique.
That isn’t too difficult:

```python
room.add_component(Room())
bob.add_component(RoomPresence(room=room.get_component(Room)._uid))
```

The `Room._uid` is generated automatically during `add_component()`, and
then the component is registered with the `World`. Now when a `System`
`CastSpellOnRoom` runs and sees that Bob does indeed cast a spell on the
room that he is in, so it tries

```python
room_uid = RoomPresence(room=room.get_component(Room)._uid
room = world.get_component(_uid)
```

to do something with the room, but if the room has already been
destroyed, `world.get_component()` will raise a
`KeyError("No such component")`. It’s now up to the system how to deal
with that, and how to bring Bob’s `RoomPresence` component back into a
consistent state.

However, it’s not this system’s *job* to clean up after `RoomPresences`,
it is to cast a spell. What it can do, or what should ideally happen
automatically, is that Bob gets marked as needing cleanup (e.g.
`bob.add_component(CleanUpRoom)`), and that a dedicated system
deals with what consistency means in the game (e.g. just removing the
component, or setting the referenced room to an empty void for the
player to enjoy). This in turn leads to possible race conditions; *when*
does that transition happen during a frame? On the other hand, since
*all* systems that can’t work properly anymore due to this inconsistent
situation should deal predictably and fail-safe (mark and proceed with
other entities) with it, this should be of preventable impact.


Implementational detail: Size of GUIDs
--------------------------------------

NOTE: Theoretical for now, there are no GUIDs being used yet.

TL;DR: 64 bit is the right answer

Entities act as nothing more than a label, and are usually implemented
as a simple integer as a globally unique identifier (GUID). The question
arises: How many of those do we need?

Assume a game of five million concurrent players, and a thousand
Entities in the game world per player. Thus we arrive at five billion
Entities in the game world. This is just above 2**32 numbers (4.29
billion). 64 bit offers over 18 quintillion IDs, which should be enough
for even the largest player base with a staggering amount of per-player
content of the game world.


Implementational detail: Systems threading
------------------------------------------

CURRENT STATE: When a system is added, an `int` is provided.
`world.update()` will run the task in order of ascending numbers.

One advantage of ECSes seems to be parallelization. Systems can run in
parallel as they are independent of each other. I think that that’s
Snake Oil, and I won’t buy it that easily.

* There is time. The basic time unit of a game is usually a frame on
  the client’s side, and a tick on the server side. A system may run as
  fast and as often as it pleases if all that is does is triggered by
  state changes on components, and thus effectively does event-driven
  processing on them. However, if that is not the case for a given
  system, then it will likely need to run once per frame/tick. Thus, a
  synchronization point between systems is needed.
* There are cause-and-effect dependencies. Consider input, physics, and
  rendering. In any given frame, these need to happen in a defined
  sequence, so that the player is presented with a consistent game
  state.
* There is no time. Every now and then, a System may need to perform a
  time-costly operation, like loading a model from disk or, even worse,
  over the network. This would bring the advantages of parallelity to
  the forefront, as only this specific system would stall, and all
  others would keep running and pick up on the results of the operation
  once it is available. This, however, can only happen if there are no
  synchronization points between those other systems and the stalling
  one.

I have no idea how to square these with each other elegantly, though
within Panda3D, the task manager can solve this. Long-running systems
into separate task chains to run asynchronous, while "every frame" tasks
are put into the default task chain.


Note: Component Inheritance Considered Dangerous
------------------------------------------------

One basic design feature of an ECS is the separation of data from the
code that processes it. One could now get the idea "Excellent, then I
can have a class hierarchy of Components, and the Systems will process
those Components that subclass their component types." The perceived
upshot here is that as gameplay is iterated on, Components can be
enriched with new functionality (implemented in Systems) that add to
existing behavior, while old behavior runs on unaltered for those
components that are still of the base component’s type. This is
unnecessary and potentially dangerous. The alternative is to just add a
new component type, and a system that runs on entities where both
components are present. This leads to easy management of the system:

* Old items should be individually upgraded, or need to be upgraded for
  the new rollout? Just add the new component, no upgrade mechanism
  necessary.
* The feature wasn’t fun after all? Remove the new Components from the
  game. No need to have a downgrade mechanism for components of the new
  type. Systems that fall into disuse can be identified automatically.
* You end up with two Systems anyway.
* Having an inheritance tree between component types also leads to a
  semantic problem: What kinds of components can exist on the same
  entity? If a base class A is used for feature 1, a child class B for
  feature 1+2, and C for 1+3, how can an entity partake in 1+2+3? It'd
  have to have both B and C, which would mean having two instances of
  the shared set of fields, and an ambiguity concerning which component
  should be used when another system uses the base type A.
* If you’re doing hierarchical inheritance on the component types, you
  incur the penalties outlined above. If you’re doing compositional
  inheritance, you’re just replicating what ECS does anyway when you add
  a new component type to an entity.



Composing templates for generic entities
----------------------------------------

Note: I’ve implemented `Aspects` with slightly different API; no
`MetaAspects` until I actually need them.

To set up entities individually, giving them their components and the
starting values of those, is repetitive and inefficient. Even writing a
factory function for each type of entity in your game is repetitive,
because in all likelihood, some kinds of entities will be very similar
to each other.

Thus we need factory functions that create entities from sets of
building blocks, and allow for overriding the given default values on a
per-entity basis. The question is: How are those building blocks put
together?

Two approaches offer themselves:

* Archetypes: Just use Python’s inheritance system. Conflicts due to
  diamond inheritance should be resolved by the usual linearization
  rules. Frankly I have not thought too deeply about this approach.
  * Pros: People who know Python know how this works
  * Cons: Didn’t we just get rid of OOP inheritance for reasons?
* Aspects: We’ll do EC-like composition again on a higher level.
  * An aspect is a set of component types (and values diverging from the
    defaults) and parent aspects. When you create an entity from a
    set of aspects, all component types get pooled. Unlike to
    Archetypes, each type must be provided only once. This disallows
    diamond inheritance and forces a pure tree inheritance.
  * This can already be checked on aspect creation
  * It also allows for testing at runtime whether an entity still
    fulfills an archetype.
  * This in turn allows for removing and adding aspects at runtime while
    insuring that aspects lower down in the hierarchy still match. An
    entity can be given several different instances of an archetype,
    only one of which can be active at any given time, but can be
    swapped out for another one.
  * API draft:
    * `Aspect(aspects_or_components, overrides=None)`
      * Creates an aspect.
      * Calling an aspect returns a set of new component instances.
      * 'overrides' provides default values to use instead of the ones
      * on the provided aspects. Calling an aspect with overrides does
        not invalidate, but possibly override, an aspect’s overrides.
    ```python
    moveset = [WalkingMovement, InertialMovement, BumpingMovement, FallingMovement]
    walker = Aspect(moveset)
    slider = Aspect(moveset, {InertialMovement: dict(acceleration=5.0)})
    world.create_entity(slider())  # A walker with acceleration of 5.0
    world.create_entity(slider({InertialMovement: dict(rotated_inertia=1.0)})))  # Acceleration is still 5.0
    ```
   * add_aspect(entity, components)
     Just a bit of syntactic sugar, and may perform a check whether
     component clashes would occur before adding any component.
   * MetaAspect(list_of_aspects)
     A MetaAspect is a list of aspects. Components can not be created
     from a MetaAspect. Its purpose is to serve as a flexible filter
     when removing aspects from an entity. Instead of of one aspect, it
     is given a list of them, which is matched in order against the
     entity. The first one to match is then removed from the entity.
   * remove_aspect(entity, aspect_or_metaaspect)
     Returns the set of removed components.

Example for Aspects:

```python
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


Articles
--------

* [Wikipedia article on ECS](https://en.wikipedia.org/wiki/Entity_component_system)
* [An MMO engineer's blog](http://t-machine.org/index.php/2007/09/03/entity-systems-are-the-future-of-mmog-development-part-1/)
* https://www.gamedevs.org/uploads/data-driven-game-object-system.pdf
