from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import LineSegs, NodePath

from wecs.aspects import Aspect
from wecs.aspects import factory
from wecs import panda3d
from wecs import mechanics
from wecs import cefconsole
from wecs.panda3d import aspects


GRIDSIZE = 2 # In meters

def build_grid(w, h, s):
    lines = LineSegs()
    lines.set_color((0,0,0,1))
    for y in range(h):
        y *= s
        lines.draw_to((w*s, y, 0))
        lines.set_color((0,0,0,1))
        lines.draw_to((h*s, y+s, 0))
        lines.draw_to((0, y+s, 0))
    lines.move_to((0, 0, 0))
    for x in range(w):
        x *= s
        lines.draw_to((x, h*s, 0))
        lines.draw_to((x+s, h*s, 0))
        lines.draw_to((x+s, 0, 0))
    lines.move_to((0, 0, 0))
    lines.draw_to((w*s, 0, 0))
    lines.draw_to((w*s, h*s, 0))
    lines.draw_to((0, h*s, 0))
    lines.draw_to((0, 0, 0))
    gridLines = lines.create()
    grid = NodePath(gridLines)
    grid.set_pos(-w+(s/2), -h+(s/2), 0)
    return grid


def load_tileset(filename, debug=False):
    tileset_model = loader.loadModel(filename)
    tileset = {}
    for tile_collection in tileset_model.find_all_matches("**/=wecs_tiles"):
        if debug: print('tileset "{}"'.format(tile_collection.name))
        tileset[tile_collection.name] = {}
        for tile in tile_collection.get_children():
            if debug: print('  tile "{}"'.format(tile.name))
            tile.set_pos(0,0,0)
            tileset[tile_collection.name][tile.name] = tile
    return tileset

system_types = [
    panda3d.LoadModels,
    mechanics.DetermineTimestep,
    panda3d.AcceptInput,
    panda3d.TurningBackToCamera,
    panda3d.UpdateCharacter,
    panda3d.Cursoring,
    panda3d.Walking,
    panda3d.ExecuteMovement,
    panda3d.Create,
    panda3d.UpdateCameras,
    cefconsole.UpdateWecsSubconsole,
    cefconsole.WatchEntitiesInSubconsole,
]

grid = build_grid(500, 500, GRIDSIZE)
game_map = Aspect(
    [
        mechanics.Clock,
        panda3d.Position,
        panda3d.Model,
        panda3d.Scene,
        panda3d.FlattenStrong,
    ],
    overrides={
        mechanics.Clock: dict(clock=panda3d.panda_clock),
        panda3d.Scene: dict(node=base.render),
        panda3d.Model: dict(node=grid),
    },
)
map_entity = base.ecs_world.create_entity()
game_map.add(map_entity)

tileset = load_tileset("../../assets/tiles.bam")
# cursor
cursor_model = tileset["other"]["cursor"]
cursor_model.set_scale(GRIDSIZE)
cursor_node = NodePath("cursor")
cursor_model.reparent_to(cursor_node)

cursor = Aspect(
    [
        aspects.character,
        panda3d.Input,
        panda3d.CursorMovement,
        panda3d.ThirdPersonCamera,
        panda3d.TurntableCamera,
        panda3d.TurningBackToCameraMovement,
        panda3d.Creator,
        cefconsole.WatchedEntity,
    ])
cursor.add(
    base.ecs_world.create_entity(),
    overrides={
        mechanics.Clock: dict(parent=map_entity._uid),
        panda3d.Position: dict(value=Point3(0, 0, 0)),
        panda3d.Model: dict(node=cursor_node),
        panda3d.ThirdPersonCamera: dict(distance=15.0, focus_height=GRIDSIZE/2),
        panda3d.TurntableCamera: dict(pitch=-90),
        panda3d.TurningBackToCamera: dict(view_axis_alignment=90),
        panda3d.CursorMovement: dict(move_snap=GRIDSIZE),
        panda3d.Creator: dict(
            tileset=tileset,
            collection="walls",
            tile_name="wall",
        ),
    },
)
