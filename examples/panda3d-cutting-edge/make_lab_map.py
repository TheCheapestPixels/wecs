from panda3d.core import NodePath
from panda3d.core import CardMaker
from panda3d.core import Material
from panda3d.core import PNMImage
from panda3d.core import Texture
from panda3d.core import TextureStage
from panda3d.core import DirectionalLight
from panda3d.core import AmbientLight


cm = CardMaker('card')
cm.set_frame(-31, 31, -31, 31)

map_np = NodePath("map")
card = map_np.attach_new_node(cm.generate())
card.set_p(-90)

mat = Material()
mat.set_base_color((1.0, 1.0, 1.0, 1))
mat.set_emission((1.0, 1.0, 1.0, 1))
mat.set_metallic(1.0)
mat.set_roughness(1.0)
card.set_material(mat)


texture_size = 256

base_color_pnm = PNMImage(texture_size, texture_size)
base_color_pnm.fill(0.72, 0.45, 0.2)  # Copper
base_color_tex = Texture("BaseColor")
base_color_tex.load(base_color_pnm)
ts = TextureStage('BaseColor') # a.k.a. Modulate
ts.set_mode(TextureStage.M_modulate)
card.set_texture(ts, base_color_tex)


# Emission; Gets multiplied with mat.emission
emission_pnm = PNMImage(texture_size, texture_size)
emission_pnm.fill(0.0, 0.0, 0.0)
emission_tex = Texture("Emission")
emission_tex.load(emission_pnm)
ts = TextureStage('Emission')
ts.set_mode(TextureStage.M_emission)
card.set_texture(ts, emission_tex)


# Ambient Occlusion, Roughness, Metallicity
# R: Ambient Occlusion
# G: Roughness, a.k.a. gloss map (if inverted); Gets multiplied with mat.roughness
# B: Metallicity; Gets multiplied with mat.metallic
metal_rough_pnm = PNMImage(texture_size, texture_size)
ambient_occlusion = 1.0
roughness = 0.18
metallicity = 0.12 # 0.98
metal_rough_pnm.fill(ambient_occlusion, roughness, metallicity)
metal_rough_tex = Texture("MetalRoughness")
metal_rough_tex.load(metal_rough_pnm)
ts = TextureStage('MetalRoughness') # a.k.a. Selector
ts.set_mode(TextureStage.M_selector)
card.set_texture(ts, metal_rough_tex)


# Normals
# RGB is the normalized normal vector (z is perpendicular to
# the surface) * 0.5 + 0.5
normal_pnm = PNMImage(texture_size, texture_size)
normal_pnm.fill(0.5, 0.5, 0.1)
normal_tex = Texture("Normals")
normal_tex.load(normal_pnm)
ts = TextureStage('Normals')
ts.set_mode(TextureStage.M_normal)
card.set_texture(ts, normal_tex)


for i in range(21):
    sp = map_np.attach_new_node(f'spawn_point_a_{i}')
    sp.set_pos(-30 + i*3, -30, 0)
    sp = map_np.attach_new_node(f'spawn_point_b_{i}')
    sp.set_pos(-30 + i*3, 30, 0)
    sp.set_h(180)


# Lights
ambient_light = map_np.attach_new_node(AmbientLight('ambient'))
ambient_light.node().set_color((.1, .1, .1, 1))
map_np.set_light(ambient_light)


direct_light = map_np.attach_new_node(DirectionalLight('light'))
direct_light.node().set_color((.8, .8, .8, 1))
map_np.set_light(direct_light)
direct_light.set_pos(0, 0, 10)
direct_light.look_at(0, 0, 0)


# Save it
map_np.write_bam_file("rectangle_map.bam")


# octaves = 2
# 
# vdata = GeomVertexData('name', format, Geom.UHStatic)
# vdata.setNumRows(4)
# 
# vertex = GeomVertexWriter(vdata, 'vertex')
# color = GeomVertexWriter(vdata, 'color')
# 
# vertex.addData3(1, 0, 0)
# color.addData4(0, 0, 1, 1)
