# WECS

WECS stands for World, Entities, Components, Systems, and is an implementation
of an ECS system.


# Design

## ECS definition


* Entities
  * have a set of Components
  * are, with regard to how they are processed, typeless
* Components
  * are the state of an Entity
  * have a type
* Systems
  * process Components of specific types (see user story below) when
    * a Component of any such type is created, for which the System's
      `init_component()` is called. This allows for setup, i.e. loading models
      into Panda3D's scene graph.
    * a Component of any such type is destroyed, calling `destroy_component()`.
      This allows for necessary breakdown.
    * the System is added to or removed from the World. This calls
      `init_component()` or `destroy_component()` respectively.
    * the System's game logic is being run, caused by
      * World.update()
      * a task that is created when the System is added to the World
* World
  * has a set of Entities
  * has a set of Systems
  * causes Systems to process their relevant Components in an appropriate
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
Thus, there are two Systems, TimestepSystem and PhysicsSystem, plus
game-specific system, here exemplified by ThrusterSystem.

* TimestepSystem
  * is run on [PhysicsWorld, PhysicsObject], meaning any component implementing
    any of these types; this is an OR filter.
  * gets the PhysicsWorld component (there is exactly one per world) and lets it
    determine the next timestep's length
  * updates all the component's timestep field
* ThrusterSystem
  * is run on [(Thruster, PhysicsObject)], meaning the components of those types
    that are on any entity that has components of all of these types. This is an
    AND filter.
* PhysicsSystem
  * is run on [PhysicsWorld]
  * runs the physics simulation


## Implementational detail: Optimizing type filtering performance

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


## Implementational detail: Size of GUIDs (TL;DR: 64 bit is the right answer)

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
