from panda3d.core import Point3
from panda3d.core import Vec3

from wecs.aspects import Aspect
from wecs.aspects import factory
from wecs import panda3d
from wecs import mechanics
from wecs import cefconsole
from wecs.panda3d import aspects


# Each frame, run these systems. This defines the game itself.
system_types = [
    panda3d.LoadModels,  # Loads models, sets up actors, makes them collibable.
    mechanics.DetermineTimestep,  # How long is this frame? Update all clocks.
    # What movement do the characters intend to do?
    panda3d.AcceptInput,  # Input from player, ranges ([-1; 1]), not scaled for time.
    panda3d.Think,  # Input from AIs, the same
    panda3d.UpdateStamina,  # A game mechanic that cancels move modes if the character is exhausted, "unintending" them
    panda3d.TurningBackToCamera,  # Characters can have a tendency towards walk towards away-from-camera that adjusts their intention.
    panda3d.UpdateCharacter,  # Scale inputs by frame time, making them "Intended movement in this frame."
    # The following systems adjust the intended movement
    panda3d.Floating,  # Scale by speed for floating
    panda3d.Walking,  # Scale by speed for walk / run / crouch / sprint
    panda3d.Inertiing,  # Clamp movement speed delta by inertia.
    panda3d.Bumping,  # Bump into things (and out again).
    panda3d.Falling,  # Fall, or stand on the ground.
    panda3d.Jumping,  # Impart upward impulse.
    panda3d.ExecuteMovement,  # Turn intention into actual movement.
    panda3d.AnimateCharacter,
    panda3d.Animate,
    panda3d.UpdateSprites,
    # We're done with character movement, now update the cameras and console.
    panda3d.UpdateCameras,
    panda3d.CollideCamerasWithTerrain,
    cefconsole.UpdateWecsSubconsole,
    cefconsole.WatchEntitiesInSubconsole,
]


# Aspects are basically classes for entities. Here are two that we will use.
game_map = Aspect(
    [mechanics.Clock,
     panda3d.Position,
     panda3d.Model,
     panda3d.Scene,
     panda3d.CollidableGeometry,
     panda3d.FlattenStrong,
    ],
    overrides={
        mechanics.Clock: dict(clock=panda3d.panda_clock),
        panda3d.Model: dict(model_name='roadE.bam'),
        panda3d.Scene: dict(node=base.render),
    },
)


# Populate the world with the map, the player character, and a few NPCs

# Map
map_entity = base.ecs_world.create_entity(name="Level geometry")
game_map.add(map_entity)

# Player
player_avatar = Aspect(
    [
        aspects.player_character,
        panda3d.Stamina,
        cefconsole.WatchedEntity,
    ])
player_avatar.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={
        mechanics.Clock: dict(parent=map_entity._uid),
        panda3d.Position: dict(value=Point3(50, 290, 0)),
    },
)

# Non-moving NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca"),
    overrides={
        panda3d.Position: dict(value=Point3(60, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)

# Small circle NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(name="Roundbecca"),
    overrides={
        panda3d.Position: dict(value=Point3(70, 290, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.25, 0.0),
            heading=-0.5,
        ),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)

# Brownian NPC
new_npc = Aspect([aspects.avatar, aspects.npc_mind_brownian])
new_npc.add(
    base.ecs_world.create_entity(name="Randombecca"),
    overrides={
        panda3d.Position: dict(value=Point3(80, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)


# Sprite
sprite = Aspect(
    [
        aspects.character,
        aspects.walking,
        panda3d.Sprite,
        panda3d.SpriteAnimation,
        cefconsole.WatchedEntity,
    ])
sprite.add(
    base.ecs_world.create_entity(name="mr. man"),
    overrides = {
        mechanics.Clock: dict(parent=map_entity._uid),
        panda3d.Sprite: dict(image_name="../../assets/mrman.png"),
        panda3d.SpriteAnimation: dict(
            animations={
                "walking" : [6, 7, 8, 9, 10, 11]
            },
            animation="walking",
        ),
        panda3d.Position: dict(value=Point3(52, 292, 0)),
    }
)
