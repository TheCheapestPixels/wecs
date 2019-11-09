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



game_map = Aspect([panda3d.Position, panda3d.Model, panda3d.Scene, Map],
                  overrides={
                      panda3d.Position: dict(value=factory(lambda:Point3(0, 0, 0))),
                      panda3d.Model: dict(model_name='roadE.bam'),
                      panda3d.Scene: dict(node=base.render),
                  },
)


# Populate the world with the map, the player character, and a few NPCs

# Map
game_map.add(base.ecs_world.create_entity())

# Player
player_avatar = Aspect([aspects.player_character, mechanics.Stamina])
player_avatar.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(50, 290, 0))},
)

# Non-moving NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(60, 290, 0))},
)

# Small circle NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(70, 290, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.25, 0.0),
            heading=-0.5,
        ),
    },
)

# Brownian NPC
new_npc = Aspect([aspects.avatar, aspects.npc_mind_brownian])
new_npc.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(80, 290, 0))},
)
