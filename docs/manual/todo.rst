TODO List
=========

Hot Topics
----------

-  Pinned tasks

   -  Update PyPI package

-  panda3d

   -  Check the ``task_mgr`` for tasks already existing at a given sort
   -  If that’s not possible, ``System``\ ify existing Panda3D ``tasks``
   -  character.Walking

      -  Decreased control while in the air
      -  Null input should have zero effect, not effect towards zero
         movement

   -  character.Jumping

      -  Multijump

-  mechanics

   -  Move ``equipment``, ``inventory``, and ``rooms`` here

-  Character animation

Lukewarm
--------

-  ``wecs.console``

   -  The current version basically only shows that functionally, it
      exists.
   -  It needs to look prettier
   -  There needs to be insight into current component values
   -  Entities should be pinnable, going to the top of the list
   -  The list should be sortable / filterable by component presence and
      values
   -  Components, and sets of them, should be drag-and-dropable from
      entity to entity
   -  There should be entity / component creation, and a “shelf” to put
      (sets of) unattached components on
   -  A waste bin that destroys entities / components dragged onto it
   -  Adding / removing aspects
   -  There should also be a column set for system membership

Icebox
------

-  Bugs

   -  CharacterController:

      -  Bumping: Go into an edge. You will find yourself sticking to it
         instead of gliding off to one side.
      -  Bumping: Go through a thin wall.
      -  Bumping: Walk into a wall at a near-perpendicular angle,
         drifting towards a corner. When the corner is reached, the
         character will take a sudden side step. Easy to see when
         walking into a tree. Probably the result not taking inertia
         into account.
      -  Falling: Stand on a mountain ridge. You will jitter up and
         down.
      -  example: Break Map / LoadMapsAndActors out of game.py

   -  CollideCamerasWithTerrain

      -  With the head stuck against a wall (e.g. in the tunnel), this
         places the camera into the wall, allowing to see through it.
      -  If the angle camera-wall and camera-character is small, the
         wall gets culled, probably due to the near plane being in the
         wall.
      -  Changes in camera distance after startup do not get respected.

-  Tests

   -  Tests for ``get_component_dependencies()`` /
      ``get_system_component_dependencies()``
   -  Is there proper component cleanup when an entity is removed?
   -  Does removing entities affect the currently running system?
   -  Coverage is… lacking.

-  Documentation

   -  More docstrings
   -  doctests

-  Development pipeline

   -  tox

-  core

   -  API improvements

      -  ``entity = world[entity_uid]``
      -  ``entity = other_entity.get_component(Reference).uid``

   -  Unique ``Components``; Only one per type in the world at any given
      time, to be tested between removing old and adding new components?
   -  De-/serialize world state

-  boilerplate

   -  Dump ``Aspect``\ s into graphviz

-  graphviz

   -  Inheritance diagrams of ``Aspect``\ s

-  panda3d

   -  character

      -  Bumpers bumping against each other, distributing the push
         between them.
      -  climbing

   -  ai

      -  Turn towards entity
      -  Move towards entity
      -  Perceive entity

   -  Debug console

-  mechanics

   -  Meter systems: i.e. Health, Mana

-  ai

   -  Hierarchical Finite State Machine
   -  Behavior Trees
   -  GOAP / STRIPS

-  All code

   -  Change ``filtered_entities`` to ``entities_by_filter``
   -  ``system.destroy_entity()`` now gets ``components_by_type``
      argument (in turn superceded by ``exit_filter_foo(self.entity)``).
   -  I’ve been really bad about implementing
      ``system.destroy_entity()``\ s…
   -  ``clock.timestep`` is deprecated. Replace with ``.wall_time``,
      ``.frame_time``, or ``.game_time``.

-  examples: Minimalistic implementations of different genres, acting as
   guideposts for system / component development.

   -  Walking simulator

      -  documents / audio logs
      -  triggering changes in the world

   -  Platformer

      -  2D or 3D? Make sure that it doesn’t matter.
      -  Minimal NPC AI

   -  Twin stick shooter

      -  Tactical NPC AI

   -  Creed-like climber
   -  Stealth game
   -  First-person shooter: “Five Minutes of Violence”
   -  Driving game: “Friction: Zero”
   -  Abstract puzzle game: “sixxis”

      -  Candidate for list culling: Probably provides no reusable
         mechanics

   -  Match 3
   -  Rhythm game

      -  Candidate for list culling: Just a specific subgenre of
         abstract puzzle games. Then again, it is a specific mechanic
         that defines a (sub)genre…

   -  Environmental puzzle game
   -  Turn-based strategy

      -  Strategic AI

   -  Real-time strategy

      -  Strategic AI

   -  Point and click
   -  Role-playing game

      -  Character sheet and randomized skill tests
      -  Talking

   -  Adventure
   -  Flight simulator
   -  City / tycoon / business / farming / life simulation
   -  Rail shooter / Shooting gallery
   -  Brawler
   -  Bullet Hell
   -  Submarine simulator
