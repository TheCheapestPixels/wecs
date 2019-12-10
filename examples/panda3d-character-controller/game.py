from panda3d.core import Point3
from panda3d.core import Vec2, Vec3
from panda3d.core import CollisionCapsule

from wecs.core import System
from wecs.core import Component
from wecs.aspects import Aspect
from wecs.aspects import factory
from wecs import panda3d
from wecs import mechanics
from wecs.panda3d import aspects
from wecs.boilerplate import Subconsole


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


class WECSSubconsole(Subconsole):
    name = "WECS"
    html = "wecs.html"
    funcs = {
        'refresh_wecs_matrix': 'refresh_wecs_matrix',
        'toggle_live_refresh_wecs_matrix': 'toggle_live_refresh_wecs_matrix',
    }
    refresh = True
    live_refresh = False

    def refresh_wecs_matrix(self):
        self.refresh = True

    def toggle_live_refresh_wecs_matrix(self):
        self.live_refresh = not self.live_refresh

    def update(self):
        if self.refresh or self.live_refresh:
            entities = base.ecs_world.entities
            uids = {repr(e._uid): e for e in entities}
            uid_list = sorted(uids.keys())
            component_types = set()
            for entity in entities:
                for component in entity.components:
                    component_types.add(type(component))
            component_types = sorted(component_types, key=lambda ct: repr(ct))
            def crepr(e, ct):
                if ct in e:
                    return e[ct]
                else:
                    return None
            matrix = [
                (uid, [crepr(uids[uid], ct) for ct in component_types])
                for uid in uid_list
            ]
            template = base.console.env.get_template('wecs_matrix.html')
            content = template.render(
                component_types=component_types,
                matrix=matrix,
            )
            self.console.exec_js_func('update_wecs_matrix', content)
            self.refresh = False


wecs_subconsole = WECSSubconsole()
base.console.add_subconsole(wecs_subconsole)


class UpdateWecsSubonsole(System):
    entity_filters = {}

    def update(self, entities_by_filter):
        wecs_subconsole.update()


# Each frame, run these systems. This defines the game itself.
system_types = [
    LoadMapsAndActors,  # Self-descriptive...
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
    panda3d.Inertiing,  # Clamp movement speed delta by inertia
    panda3d.Bumping,  # Bump into things (and out again).
    panda3d.Falling,  # Fall, or stand on the ground.
    panda3d.Jumping,  # Impart upward impulse.
    panda3d.ExecuteMovement,  # Turn intention into actual movement
    panda3d.AnimateCharacter,
    panda3d.Animate,
    # We're done with character movement, now adjust the cameras.
    panda3d.UpdateCameras,
    panda3d.CollideCamerasWithTerrain,
    UpdateWecsSubonsole,
]


def panda_clock():
    def read_dt():
        return globalClock.dt
    return read_dt


game_map = Aspect(
    [mechanics.Clock,
     panda3d.Position,
     panda3d.Model,
     panda3d.Scene,
     Map,
    ],
    overrides={
        mechanics.Clock: dict(clock=panda_clock),
        panda3d.Position: dict(value=factory(lambda:Point3(0, 0, 0))),
        panda3d.Model: dict(model_name='roadE.bam'),
        # panda3d.Model: dict(model_name='grid.bam'),
        panda3d.Scene: dict(node=base.render),
    },
)


# Populate the world with the map, the player character, and a few NPCs

# Map
map_entity = base.ecs_world.create_entity()
game_map.add(map_entity)

# Player
player_avatar = Aspect([aspects.player_character, panda3d.Stamina])
player_avatar.add(
    base.ecs_world.create_entity(),
    overrides={
        mechanics.Clock: dict(parent=map_entity._uid),
        panda3d.Position: dict(value=Point3(50, 290, 0)),
    },
)

# Non-moving NPC
aspects.non_player_character.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(60, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
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
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)

# Brownian NPC
new_npc = Aspect([aspects.avatar, aspects.npc_mind_brownian])
new_npc.add(
    base.ecs_world.create_entity(),
    overrides={
        panda3d.Position: dict(value=Point3(80, 290, 0)),
        mechanics.Clock: dict(parent=map_entity._uid),
    },
)
