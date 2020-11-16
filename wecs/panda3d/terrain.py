"""
"""

from dataclasses import field

from panda3d.core import ShaderTerrainMesh
from panda3d.core import SamplerState
from panda3d.core import NodePath
from panda3d.core import PNMImage
from panda3d.core import Texture

from wecs.panda3d.prototype import Model
from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID


@Component()
class GPUTerrain:
    """
    a renderable Heightfield terrain object

    :param ShaderTerrainMesh terrain: Native Panda3d ShaderTerrainMesh object
    :param NodePath node: The scene graph object representing the ShaderterrainMesh
    :param str heightfield: File path pointing to the the heightfield to load
    :param float target_triangle_width: Sets the target triangle width. Defaults to a value of 10.0
    :param int chunk_size: This sets the chunk size of the terrain. Defaults to 16
    :param float scale_z: Z height scaling of the terrain. Leave at default 0 to auto calculate based on heightmap size
    """

    terrain: ShaderTerrainMesh = field(default_factory=ShaderTerrainMesh)
    node: NodePath = field(default_factory=lambda: NodePath(""))
    heightfield: str = None
    target_triangle_width: float = 10.0
    chunk_size: int = 16
    scale_z: float = 0

class ManageTerrain(System):
    """
    Handles Terrain component management and setup

        Components used :func:`wecs.core.and_filter` `GPUTerrain`
            | :class:`wecs.panda3d.mode.Model`
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
        heightfield_buffer = PNMImage()
        heightfield_buffer.read(terrain.heightfield)

        heightfield = Texture()
        heightfield.load(heightfield_buffer)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        terrain.terrain.heightfield = heightfield

        # Set the target triangle width. For a value of 10.0 for example,
        # the terrain will attempt to make every triangle 10 pixels wide on screen.
        terrain.terrain.target_triangle_width = terrain.target_triangle_width

        # Sets the terrains chunk size
        terrain.terrain.set_chunk_size(terrain.chunk_size)

        # Generate the terrain NodePath and attach it to our model
        terrain.terrain.generate()
        terrain.node = geometry.node.attach_new_node(terrain.terrain)

        # Set our terrain's calculated scale value using the size of the heightfield as
        # the scale input
        scale_x = heightfield_buffer.get_x_size()
        scale_y = heightfield_buffer.get_y_size()

        if terrain.scale_z == 0:
            scale_z = scale_x * 0.09765625
        else:
            scale_z = terrain.scale_z
        terrain.node.set_scale(scale_x, scale_y, scale_z)

