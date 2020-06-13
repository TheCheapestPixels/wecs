from panda3d.core import Point3
from panda3d.core import Vec3

from wecs import cefconsole
from wecs import mechanics
from wecs import panda3d as wp3d
from wecs.aspects import Aspect
from wecs.panda3d import aspects
from wecs.panda3d import debug

# Each frame, run these systems. This defines the game itself.
system_types = [  # fixme boilerplate states that system_types are deprecated.
    wp3d.ManageGeometry,  # Manages a model's geometry and its nodepaths.
    wp3d.SetupModels,  # Makes them collibable.
    wp3d.PrepareCameras,  # Attach / detach camera pivots to / from models.
    wp3d.UpdateClocks,  # How long is this frame? Update all clocks.
    # What movement do the characters intend to do?
    # wp3dAcceptInput,  # Input from player, ranges ([-1; 1]), not scaled for time.
    wp3d.Think,  # Input from AIs, the same
    wp3d.UpdateStamina,  # A game mechanic that cancels move modes if the character is exhausted, "unintending" them
    wp3d.UpdateCharacter,  # Scale inputs by frame time, making them "Intended movement in this frame."
    # The following systems adjust the intended movement
    wp3d.Floating,  # Scale by speed for floating
    wp3d.Walking,  # Scale by speed for walk / run / crouch / sprint
    wp3d.Inertiing,  # Clamp movement speed delta by inertia.
    wp3d.Bumping,  # Bump into things (and out again).
    wp3d.Falling,  # Fall, or stand on the ground.
    wp3d.Jumping,  # Impart upward impulse.
    wp3d.TurningBackToCamera,  # Head towards where the camera is pointing.
    wp3d.ExecuteMovement,  # Turn intention into actual movement.
    wp3d.AnimateCharacter,
    wp3d.Animate,
    wp3d.UpdateSprites,
    # We're done with character movement, now update the cameras and console.
    wp3d.ResetMountedCamera,
    wp3d.ReorientObjectCentricCamera,
    wp3d.CollideCamerasWithTerrain,
    wp3d.UpdateBillboards,
    cefconsole.UpdateWecsSubconsole,
    cefconsole.WatchEntitiesInSubconsole,
    debug.DebugTools,
]

# Aspects are basically classes for entities. Here are two that we will use.
game_map = Aspect(
    [mechanics.Clock,
     wp3d.Position,
     wp3d.Model,
     wp3d.Geometry,
     wp3d.Scene,
     wp3d.CollidableGeometry,
     wp3d.FlattenStrong,
     ],
    overrides={
        mechanics.Clock: dict(clock=wp3d.panda_clock),
        wp3d.Geometry: dict(file='roadE.bam'),
        wp3d.Scene: dict(node=base.render),
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
        wp3d.Stamina,
        cefconsole.WatchedEntity,
    ])
player_avatar.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={
        mechanics.Clock: dict(parent=map_entity._uid),
        wp3d.Position: dict(value=Point3(50, 290, 0)),
    },
)

# Non-moving NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca"),
    overrides={
        wp3d.Position: dict(value=Point3(60, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)

# Small circle NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(name="Roundbecca"),
    overrides={
        wp3d.Position: dict(value=Point3(70, 290, 0)),
        wp3d.ConstantCharacterAI: dict(
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
        wp3d.Position: dict(value=Point3(80, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)

# Sprite
sprite = Aspect(
    [
        aspects.character,
        aspects.walking,
        wp3d.ConstantCharacterAI,
        wp3d.Sprite,
        wp3d.SpriteSheet,
        wp3d.SpriteAnimation,
        wp3d.Billboard,
        cefconsole.WatchedEntity,
    ])
sprite.add(
    base.ecs_world.create_entity(name="mr. man"),
    overrides={
        mechanics.Clock: dict(parent=map_entity._uid),
        wp3d.Sprite: dict(image_name="../../assets/mrman.png"),
        wp3d.SpriteAnimation: dict(
            animations={
                "walking": [6, 7, 8, 9, 10, 11]
            },
            animation="walking",
        ),
        wp3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.25, 0.0),
            heading=-0.5,
        ),
        wp3d.Position: dict(value=Point3(52, 292, 0)),
    }
)
