import sys
from math import sin
from math import cos
from math import sqrt
from random import gauss

from panda3d.core import Vec2
from panda3d.core import Vec3
from panda3d.core import CardMaker
from panda3d.core import Material
from panda3d.core import PNMImage
from panda3d.core import Texture
from panda3d.core import TextureStage
from panda3d.core import DirectionalLight
from panda3d.core import AmbientLight

from direct.showbase.ShowBase import ShowBase
from direct.filter.CommonFilters import CommonFilters

import simplepbr


ShowBase()
base.accept('escape', sys.exit)
def debug():
    import pdb
    pdb.set_trace()
base.accept('f11', debug)
base.set_frame_rate_meter(True)
base.cam.set_pos(0, -5, 0)
base.cam.look_at(0, 0, 0)
global pipeline
pipeline = simplepbr.init(
    msaa_samples=1,
    max_lights=8,
    #enable_shadows=True,
)
pipeline.use_normal_maps = False
pipeline.use_emission_maps = True
pipeline.use_occlusion_maps = True


cm = CardMaker('card')


cm.set_frame(-1, 1, -1, 1)
card_np = base.render.attach_new_node(cm.generate())


mat = Material()
mat.set_base_color((1.0, 1.0, 1.0, 1))
mat.set_emission((1.0, 1.0, 1.0, 1))
mat.set_metallic(1.0)
mat.set_roughness(1.0)
card_np.set_material(mat)


texture_size = 256
texture_bands_x = 2
texture_bands_y = 2


# Base color, a.k.a. Modulate, a.k.a. albedo map
# Gets multiplied with mat.base_color
base_color_pnm = PNMImage(texture_size, texture_size)
base_color_pnm.fill(0.72, 0.45, 0.2)  # Copper
base_color_tex = Texture("BaseColor")
base_color_tex.load(base_color_pnm)
ts = TextureStage('BaseColor') # a.k.a. Modulate
ts.set_mode(TextureStage.M_modulate)
card_np.set_texture(ts, base_color_tex)


# Emission; Gets multiplied with mat.emission
emission_pnm = PNMImage(texture_size, texture_size)
emission_pnm.fill(0.0, 0.0, 0.0)
emission_tex = Texture("Emission")
emission_tex.load(emission_pnm)
ts = TextureStage('Emission')
ts.set_mode(TextureStage.M_emission)
card_np.set_texture(ts, emission_tex)


# Ambient Occlusion, Roughness, Metallicity
# R: Ambient Occlusion
# G: Roughness, a.k.a. gloss map (if inverted); Gets multiplied with mat.roughness
# B: Metallicity; Gets multiplied with mat.metallic
metal_rough_pnm = PNMImage(texture_size, texture_size)
for x in range(texture_size):
    x_band = int(float(x) / float(texture_size) * (texture_bands_x))
    x_band_base = float(x_band) / float(texture_bands_x - 1)
    for y in range(texture_size):
        y_band = int(float(y) / float(texture_size) * (texture_bands_y))
        y_band_base = float(y_band) / float(texture_bands_y - 1)
        ambient_occlusion = 1.0
        roughness = x_band_base * 0.18 + 0.12  # 0.12 - 0.3
        metallicity = y_band_base * 0.1 + 0.88  # 0.1 - 0.98
        metal_rough_pnm.set_xel(x, y, (ambient_occlusion, roughness, metallicity))
metal_rough_tex = Texture("MetalRoughness")
metal_rough_tex.load(metal_rough_pnm)
ts = TextureStage('MetalRoughness') # a.k.a. Selector
ts.set_mode(TextureStage.M_selector)
card_np.set_texture(ts, metal_rough_tex)


# Normals
# RGB is the normalized normal vector (z is perpendicular to
# the surface) * 0.5 + 0.5
normal_pnm = PNMImage(texture_size, texture_size)
for x in range(texture_size):
    for y in range(texture_size):
        v = Vec3(gauss(0, 0.2), gauss(0, 0.2), 1)
        v.normalize()
        normal_pnm.set_xel(x, y, v * 0.5 + 0.5)
normal_tex = Texture("Normals")
normal_tex.load(normal_pnm)
ts = TextureStage('Normals')
ts.set_mode(TextureStage.M_normal)
card_np.set_texture(ts, normal_tex)


# cm.set_frame(-50, 50, -50, 50)
# map_np = base.render.attach_new_node(cm.generate())
# map_np.set_p(-90)
# map_np.set_z(-2)
# map_np.set_material(mat)


ambient_light = base.render.attach_new_node(AmbientLight('ambient'))
ambient_light.node().set_color((.1, .1, .1, 1))
base.render.set_light(ambient_light)


direct_light = base.render.attach_new_node(DirectionalLight('light'))
direct_light.node().set_color((.2, .2, .2, 1))
base.render.set_light(direct_light)
direct_light.set_pos(0, -100, 100)
direct_light.look_at(0, 0, 0)


def rotate_card(task):
    card_np.set_p(-22.5 + sin(task.time / 3.0 * 3) * 5.0)
    card_np.set_h(cos(task.time / 3.0) * 5.0)
    return task.cont
base.taskMgr.add(rotate_card)

base.run()
