from panda3d.core import Point3
from panda3d.core import Vec2, Vec3
from panda3d.core import CollisionCapsule

from wecs.core import Component
from wecs.aspects import Aspect
from wecs.aspects import factory
from wecs import panda3d
from wecs import mechanics
from wecs.panda3d import aspects


# Ignore this for the moment please; It means "This entity's model can be collided into".
@Component()
class Map:
    pass


# Ignore this too; It makes the map collidable.
class LoadMapsAndActors(panda3d.LoadModels):
    def post_load_hook(self, node, entity):
        if Map in entity:
            node.flatten_strong()
            node.set_collide_mask(1<<0)


# Each frame, run these systems. This defines the game itself.
system_types = [
    LoadMapsAndActors,  # Self-descriptive...
    panda3d.DetermineTimestep,  # How long is this frame? Update all clocks.
    # What movement do the characters intend to do?
    panda3d.AcceptInput,  # Input from player, ranges ([-1; 1]), not scaled for time.
    panda3d.Think,  # Input from AIs, the same
    mechanics.UpdateStamina,  # A game mechanic that cancels move modes if the character is exhausted, "unintending" them
    panda3d.TurningBackToCamera,  # Characters can have a tendency towards walk towards away-from-camera that adjusts their intention.
    panda3d.UpdateCharacter,  # Scale inputs by frame time, making them "Intended movement in this frame."
    # The following systems adjust the intended movement
    panda3d.Floating,  # Scale by speed for floating
    panda3d.Walking,  # Scale by speed for walk / run / crouch / sprint
    panda3d.Inertiing,  # Clamp movement speed delta by inertia
    panda3d.Bumping,  # Bump into things (and out again).
    panda3d.Falling,  # Fall, or stand on the ground.
    panda3d.Jumping,  # Impart upward impulse.
    panda3d.ExecuteMovement,  # Turn intention into actual movement
    # We're done with character movement, now adjust the cameras.
    panda3d.UpdateCameras,
    panda3d.CollideCamerasWithTerrain,
]


# An ontology of aspects:
# * Controllable beings on the map
#   `character`s are controllable entities with a "physical" presence (a Model)
#   `walking` is the ability to move around and interact with the map
#   An `avatar` is a character that can walk and has stamina
#   A `spectator` is a character that floats and bumps into the map.
# * Things that control beings
#   `pc_mind` represents the input from the neural network between the player's ears.
#   `npc_mind` is a mind that executes a constant movement
# * Things that see the world
#   `first_person` is a first person camera
#   `third_person` is, unsurprisingly, a third person camera (with a few features).
# * Abstractions that are actually useful
#   The `player_character` is an `avatar` controlled by a `pc_mind` and seen through
#     the `third_person` camera.
#   A `non_player_character` is an `avatar` controlled by an `npc_mind`
#   A `game_map` is a model that you can bump / fall into.

game_map = Aspect([panda3d.Position, panda3d.Model, panda3d.Scene, Map],
                  overrides={
                      panda3d.Position: dict(value=factory(lambda:Point3(0, 0, 0))),
                      panda3d.Model: dict(model_name='roadE.bam'),
                      panda3d.Scene: dict(node=base.render),
                  },
)


# Populate the world with the map, the player character, and a few NPCs
game_map.add(base.ecs_world.create_entity())

player_avatar = Aspect([aspects.player_character, mechanics.Stamina])

player_avatar.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(50, 295, 0))},
)
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(50, 300, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.25, 0.0),
            heading=-0.5,
        ),
    },
)
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(60, 300, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.75, 0.0),
            heading=-0.1,
        ),
    },
)
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(60, 295, 0))},
)
