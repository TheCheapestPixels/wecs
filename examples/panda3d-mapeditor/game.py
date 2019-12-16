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

def build_grid(x_size, y_size, s):
    lines = LineSegs()
    lines.set_color((0,0,0,1))
    for x in range(x_size):
        lines.move_to(x*s, 0, 0)
        lines.draw_to(x*s, y_size*s, 0)
    for y in range(y_size):
        lines.move_to(0, y*s, 0)
        lines.draw_to(x_size*s, y*s, 0)
    grid = NodePath(lines.create())
    grid.set_pos(-x_size+(s/2), -y_size+(s/2), 0)
    return grid


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
    panda3d.UpdateMapEditorSubconsole,
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

cursor_node = NodePath("cursor")
cursor_model = loader.loadModel("../../assets/cursor.bam")
cursor_model.set_scale(GRIDSIZE)
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
    },
)
