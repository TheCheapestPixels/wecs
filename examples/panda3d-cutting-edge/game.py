import assetcoop

import wecs

import aspects
import avatar_ui


# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.spawnpoints.Spawn,
    wecs.panda3d.camera.PrepareCameras,
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Interface interactions
    wecs.panda3d.mouseover.MouseOverOnEntity,
    wecs.panda3d.mouseover.UpdateMouseOverUI,
    avatar_ui.AvatarUI,
    # Set inputs to the character controller
    wecs.panda3d.ai.Think,
    wecs.panda3d.ai.BehaviorInhibitsDirectCharacterControl,
    wecs.panda3d.character.UpdateCharacter,
    # Fudge the inputs to achieve the kind of control that you want
    wecs.panda3d.character.ReorientInputBasedOnCamera,
    # Character controller
    wecs.panda3d.character.Floating,
    wecs.panda3d.character.Walking,
    wecs.panda3d.character.Inertiing,
    wecs.panda3d.character.Bumping,
    wecs.panda3d.character.Falling,
    wecs.panda3d.character.Jumping,
    wecs.panda3d.character.DirectlyIndicateDirection,
    wecs.panda3d.character.TurningBackToCamera,
    wecs.panda3d.character.AutomaticallyTurnTowardsDirection,
    wecs.panda3d.character.ExecuteMovement,
    # Animation
    wecs.panda3d.animation.AnimateCharacter,
    wecs.panda3d.animation.Animate,
    # Camera
    wecs.panda3d.camera.ReorientObjectCentricCamera,
    wecs.panda3d.camera.ZoomObjectCentricCamera,
    wecs.panda3d.camera.CollideCamerasWithTerrain,
    # Debug keys (`escape` to close, etc.)
    wecs.panda3d.debug.DebugTools,
]


aspects.game_map.add(
    base.ecs_world.create_entity(name="Level geometry"),
    overrides={
        wecs.panda3d.prototype.Geometry: dict(
            #file='models/scenes/lona.bam',
            file='rectangle_map.bam',
        ),
    },
)


#aspects.observer.add(
aspects.player_character.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={
        wecs.panda3d.spawnpoints.SpawnAt: dict(
            #name='spawn_player_a',
            name='spawn_point_a_10',
        ),
        **aspects.rebecca,
    },
)


for i in range(0, 21, 9):
    aspects.non_player_character.add(
        base.ecs_world.create_entity(name="NonPlayerbecca_{i}"),
        overrides={
            wecs.panda3d.spawnpoints.SpawnAt: dict(
                name=f'spawn_point_b_{i}',
            ),
            **aspects.rebecca,
        },
    )




# aspects.non_player_character.add(
#     base.ecs_world.create_entity(name="NonPlayerbecca_1"),
#     overrides={
#         wecs.panda3d.spawnpoints.SpawnAt: dict(
#             name='spawn_player_a',
#         ),
#         **aspects.rebecca,
#     },
# )
# 
# 
# aspects.non_player_character.add(
#     base.ecs_world.create_entity(name="NonPlayerbecca_2"),
#     overrides={
#         wecs.panda3d.spawnpoints.SpawnAt: dict(
#             name='spawn_player_b',
#         ),
#         **aspects.rebecca,
#     },
# )
# 
# 
# aspects.non_player_character.add(
#     base.ecs_world.create_entity(name="NonPlayerbecca_3"),
#     overrides={
#         wecs.panda3d.spawnpoints.SpawnAt: dict(
#             name='spawn_player_c',
#         ),
#         **aspects.rebecca,
#     },
# )
