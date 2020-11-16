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
class Terrain:
    """
    a renderable Heightfield terrain object

    :param ShaderTerrainMesh terrain: Native Panda3d ShaderTerrainMesh object
    :param NodePath node: The scene graph object representing the ShaderterrainMesh
    :param str heightfield: File path pointing to the the heightfield to load
    :param float target_triangle_width: Sets the target triangle width. Defaults to a value of 10.0
    :param bool generate_patches: If this option is set to true, GeomPatches will be used instead of GeomTriangles. This is required when the terrain is used with tesselation shaders
    :param int chunk_size: This sets the chunk size of the terrain. Defaults to 16
    :param float scale_z: Z height scaling of the terrain. Leave at default 0 to auto calculate based on heightmap size
    """

    terrain: ShaderTerrainMesh = field(default_factory=ShaderTerrainMesh)
    node: NodePath = None
    heightfield: str = None
    target_triangle_width: float = 10.0
    generate_patches: bool = False
    chunk_size: int = 16
    scale_z: float = 0

class ManageTerrain(System):
    """
    Handles Terrain component management and setup

        Components used in this system are
            | :func:`wecs.core.and_filter` 
            | :class:`Terrain` 
            | :class:`wecs.panda3d.mode.Model`
    """

    entity_filters = {
        'terrain': and_filter(Model, Terrain),
    }

    def enter_filter_terrain(self, entity):
        """
        Handles the creation/attachment of Terrain components
        """

        # Retrieve our Model and Terrain components
        model = entity[Model]
        terrain = entity[Terrain]

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

        # Set our generate patches flag. This is required when the terrain is used with tesselation shaders, 
        # since patches are required for tesselation, whereas triangles are required for regular rendering.
        terrain.terrain.set_generate_patches(terrain.generate_patches)

        # Generate the terrain NodePath and attach it to our model
        terrain.terrain.generate()
        if terrain.node != None:
            terrain.node.reparent_to(model.node)
        else:
            terrain.node = model.node.attach_new_node(terrain.terrain)

        # Set our terrain's calculated scale value using the size of the heightfield as
        # the scale input
        scale_x = heightfield_buffer.get_x_size()
        scale_y = heightfield_buffer.get_y_size()

        if terrain.scale_z == 0:
            scale_z = scale_x * 0.09765625
        else:
            scale_z = terrain.scale_z
        terrain.node.set_scale(scale_x, scale_y, scale_z)

    def exit_filter_terrain(self, entity):
        """
        Handles the detachment/destruction of Terrain components
        """

        # Get our terrain component and detach the node
        terrain = entity[Terrain]
        if terrain.node != None:
            terrain.node.detach_node()