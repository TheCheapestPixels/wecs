from panda3d.core import Point3
from panda3d.core import Vec2, Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionSphere
from panda3d.core import CollisionCapsule

from wecs.core import Component
from wecs.aspects import Aspect
from wecs.aspects import factory
from wecs import panda3d
from wecs import mechanics


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


character = Aspect([panda3d.Clock, panda3d.Position, panda3d.Scene,
                    panda3d.CharacterController, panda3d.Model],
                   overrides = {
                       panda3d.Clock: dict(clock=globalClock),
                       panda3d.Scene: dict(node=base.render),
                   }
)
def rebecca_bumper():
    return {
        'bumper': dict(
            shape=CollisionSphere,
            center=Vec3(0.0, 0.0, 1.0),
            radius=0.7,
        ),
    }
def rebecca_lifter():
    return {
        'lifter': dict(
            shape=CollisionSphere,
            center=Vec3(0.0, 0.0, 0.25),
            radius=0.5,
        ),
    }
walking = Aspect([panda3d.WalkingMovement, panda3d.CrouchingMovement, panda3d.SprintingMovement,
                  panda3d.InertialMovement, panda3d.BumpingMovement, panda3d.FallingMovement,
                  panda3d.JumpingMovement],
                 overrides = {
                     panda3d.InertialMovement: dict(acceleration=30.0, rotated_inertia=0.5),
                     panda3d.BumpingMovement: dict(solids=factory(rebecca_bumper)),
                     panda3d.FallingMovement: dict(solids=factory(rebecca_lifter)),
                     panda3d.JumpingMovement: dict(impulse=factory(lambda: Vec3(0, 0, 6))),
                 },
)
avatar = Aspect([character, walking, mechanics.Stamina],
                overrides={panda3d.Model: dict(model_name='rebecca.bam')})
def spectator_bumper():
    return dict(
        solids={
            'bumper': dict(
                shape=CollisionSphere,
                center=Vec3(0.0, 0.0, 0.0),
                radius=0.1,
            ),
        },
    )
spectator = Aspect([character, panda3d.FloatingMovement, panda3d.BumpingMovement],
                   overrides={
                       panda3d.Model: dict(node=factory(lambda:NodePath('spectator'))),
                       panda3d.BumpingMovement: dict(solids=factory(spectator_bumper)),
                   },
)


pc_mind = Aspect([panda3d.Input])
npc_mind = Aspect([panda3d.ConstantCharacterAI])


first_person = Aspect([panda3d.FirstPersonCamera],
                      overrides={panda3d.FirstPersonCamera: dict(camera=base.cam)})
third_person = Aspect([panda3d.TurntableCamera, panda3d.TurningBackToCameraMovement,
                       panda3d.CollisionZoom, panda3d.ThirdPersonCamera],
                      overrides={
                          panda3d.ThirdPersonCamera: dict(
                              camera=base.cam,
                              focus_height=1.8,
                          ),
                      },
)


player_character = Aspect([avatar, pc_mind, third_person])
non_player_character = Aspect([avatar, npc_mind])


# Populate the world with the map, the player character, and a few NPCs
game_map.add(base.ecs_world.create_entity())
player_character.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(50, 295, 0))},
)
non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(50, 300, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=factory(lambda:Vec3(0.0, 0.25, 0.0)),
            heading=-0.5,
        ),
    },
)
non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(60, 300, 0)),
        panda3d.ConstantCharacterAI: dict(
            move=Vec3(0.0, 0.75, 0.0),
            heading=-0.1,
        ),
    },
)
non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={panda3d.Position: dict(value=Point3(60, 295, 0))},
)
