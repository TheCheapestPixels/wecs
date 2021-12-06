import wecs

import aspects


# Each frame, run these systems. This defines the game itself.
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras,
    # Update clocks
    wecs.mechanics.clock.DetermineTimestep,
    # Interface interactions
    wecs.panda3d.mouseover.MouseOverOnEntity,
    wecs.panda3d.mouseover.UpdateMouseOverUI,
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


# Now let's create Rebeccas at the spawn points:

aspects.player_character.add(
    base.ecs_world.create_entity(name="Playerbecca"),
    overrides={
        **aspects.rebecca,
        **aspects.spawn_point_1,
    },
)

aspects.non_player_character.add(
    base.ecs_world.create_entity(name="Rebecca 1"),
    overrides={
        **aspects.rebecca,
        **aspects.spawn_point_2,
    },
)
