from panda3d.core import NodePath
from panda3d.core import Point3
from panda3d.core import LineSegs

from wecs import panda3d
from wecs import mechanics
from wecs.panda3d import aspects


system_types = [
    panda3d.LoadModels,
    mechanics.DetermineTimestep,
    panda3d.AcceptInput,
    panda3d.UpdateCharacter,
    panda3d.Cursoring, # Horizontal movement with optional grid-snapping.
    panda3d.ExecuteMovement,
    panda3d.Create, # Update creator entities.
    panda3d.UpdateCameras,
    panda3d.UpdateMapEditorSubconsole, # Interacting with map editor gui.
]

# empty scene with a grid.
def build_grid(x_size, y_size, s):
    lines = LineSegs()
    lines.set_color((0,0,0,1))
    offset = s/2
    for x in range(x_size):
        x = (x*s) - offset
        lines.move_to(x, -offset, 0)
        lines.draw_to(x, (y_size*s)-offset, 0)
    for y in range(y_size):
        y = (y*s) - offset
        lines.move_to(-offset, y, 0)
        lines.draw_to((x_size*s)-offset, y, 0)
    grid = NodePath(lines.create())
    return grid
gridsize = 500 # Size of grid in cells
cellsize = 2 # Size of cells in meters
aspects.empty_scene.add(
    base.ecs_world.create_entity(),
    overrides = {
        panda3d.Model: dict(node=build_grid(gridsize, gridsize, cellsize)),
    }
)

# cursor entity.
cursor_node = NodePath("cursor")
cursor_model = loader.loadModel("../../assets/cursor.bam")
cursor_model.set_scale(cellsize)
cursor_model.reparent_to(cursor_node)
aspects.cursor.add(
    base.ecs_world.create_entity(),
    overrides={
            panda3d.ThirdPersonCamera: dict(distance=15.0, focus_height=0),
            panda3d.TurntableCamera: dict(pitch=-90),
            panda3d.CursorMovement: dict(move_snap=cellsize),
            panda3d.Model: dict(node=cursor_node),
            panda3d.Position: dict(value=Point3(gridsize/2, gridsize/2, 0)),
    }
)
