from panda3d.core import NodePath
from panda3d.core import Point3
from panda3d.core import LineSegs

from wecs import panda3d
from wecs import mechanics
from wecs.aspects import Aspect
from wecs.panda3d import aspects
from wecs.panda3d.helpers import draw_grid

system_types = [
    panda3d.LoadModels,
    mechanics.DetermineTimestep,
    panda3d.AcceptInput,
    panda3d.UpdateCharacter,
    panda3d.Cursoring, # Horizontal movement with optional grid-snapping.
    panda3d.ExecuteMovement,
    panda3d.UpdateCameras,
    panda3d.UpdateMapEditor, # Handles Creator and Tilemap (to be split up later)
]

# empty scene with a grid.
gridsize = 500 # Size of grid in cells
cellsize = 2 # Size of cells in meters
aspects.empty_scene.add(
    base.ecs_world.create_entity(),
    overrides = {
        panda3d.Model: dict(node=draw_grid(gridsize, gridsize, cellsize)),
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
