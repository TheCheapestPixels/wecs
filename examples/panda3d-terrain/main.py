#!/usr/bin/env python
import sys

from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState, load_prc_file_data, Shader

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.mechanics import clock
from wecs.panda3d import ECSShowBase
from wecs.panda3d import prototype
from wecs.panda3d import terrain

def main():
    """
    Main entry point into the panda3d-terrain demo for WECS
    """

    # Load some configuration variables, its important for this to happen
    # before the ShowBase is initialized
    load_prc_file_data("", """
        textures-power-2 none
        gl-coordinate-system default
        window-title WECS Panda3D ShaderTerrainMesh Demo

        # As an optimization, set this to the maximum number of cameras
        # or lights that will be rendering the terrain at any given time.
        stm-max-views 8

        # Further optimize the performance by reducing this to the max
        # number of chunks that will be visible at any given time.
        stm-max-chunk-count 2048
    """)

    # Create our ShowBase instance
    base = ECSShowBase()
    base.accept('escape', sys.exit)

    # Increase camera FOV as well as the far plane
    base.camLens.set_fov(90)
    base.camLens.set_near_far(0.1, 50000)

    system_types = [
        prototype.ManageModels,
        terrain.ManageTerrain
    ]
    for sort, system_type in enumerate(system_types):
        base.add_system(system_type(), sort)

    def configure_texture(entity):
        """
        Configures the terrain's rendered texture
        after creation
        """

        model = entity[prototype.Model]
        model.node.set_texture(base.loader.load_texture('textures/grass.png'))

    # Create terrain entity
    base.ecs_world.create_entity(
        prototype.Model(
            post_attach=configure_texture),
        terrain.Terrain(
            heightfield='heightfield.png',
            target_triangle_width=10.0),
        prototype.Shader(
            shader_type=Shader.SL_GLSL,
            vertex_shader='terrain.vert.glsl',
            fragment_shader='terrain.frag.glsl',
            shader_inputs={'camera': base.camera}))

    # Start our showbase instance
    base.run()

# Main entry point into the panda3d-terrain demo for WECS
if __name__ == '__main__':
    main()
