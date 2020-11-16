"""
"""

from dataclasses import field

from panda3d.core import ShaderTerrainMesh
from panda3d.core import SamplerState
from panda3d.core import NodePath

from wecs.panda3d.prototype import Model
from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID


@Component()
class GPUTerrain:
    """
    """

    terrain: ShaderTerrainMesh = field(default_factory=ShaderTerrainMesh)
    node: NodePath = field(default_factory=lambda: NodePath(""))
    heightfield: str = None
    target_triangle_width: float = 10.0


class ManageTerrain(System):
    """
    """

    entity_filters = {
        'gpu_terrain': and_filter(Model, GPUTerrain)
    }

    def enter_filter_gpu_terrain(self, entity):
        # Retrieve our Model and GPUTerrain components
        geometry = entity[Model]
        terrain = entity[GPUTerrain]

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        heightfield = base.loader.load_texture(terrain.heightfield)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain.terrain.heightfield = heightfield

        # Set the target triangle width. For a value of 10.0 for example,
        # the terrain will attempt to make every triangle 10 pixels wide on screen.
        terrain.terrain.target_triangle_width = terrain.target_triangle_width

        ## Generate the terrain NodePath and attach it to our model
        terrain.terrain.generate()
        terrain.node = geometry.node.attach_new_node(terrain.terrain)
        terrain.node.set_scale(1024, 1024, 100) #TODO: calculate

