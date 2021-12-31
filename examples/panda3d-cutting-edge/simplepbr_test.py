import sys
from math import sin
from math import cos

from direct.showbase.ShowBase import ShowBase

from panda3d.core import CardMaker
from panda3d.core import Material
from panda3d.core import TextureStage
from panda3d.core import DirectionalLight
from panda3d.core import AmbientLight

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
pipeline.use_occlusion_maps = False


cm = CardMaker('card')


cm.set_frame(-1, 1, -1, 1)
card_np = base.render.attach_new_node(cm.generate())


mat = Material()
mat.set_ambient((0.5, 0.5, 0.5, 1))
mat.set_diffuse((0.5, 0.5, 0.5, 1))
#mat.set_emission((0.1, 0.1, 0.1, 1))
mat.set_emission((0.0, 0.0, 0.0, 1))
mat.set_shininess(5.0)
mat.set_specular((0, 1, 0, 1))
mat.set_metallic(0.1)
mat.set_roughness(0.1)
card_np.set_material(mat)


ts = TextureStage('Modulate')
ts.set_mode(TextureStage.M_modulate)
card_np.set_texture(ts, base.loader.loadTexture('Gravel022_1K_Color.png'))
ts = TextureStage('Emission')
ts.set_mode(TextureStage.M_emission)
card_np.set_texture(ts, base.loader.loadTexture('maps/color-grid.rgb'))
ts = TextureStage('Selector')
ts.set_mode(TextureStage.M_selector)
card_np.set_texture(ts, base.loader.loadTexture('Gravel022_1K_Roughness.png'))
ts = TextureStage('Normals')
ts.set_mode(TextureStage.M_normal)
card_np.set_texture(ts, base.loader.loadTexture('Gravel022_1K_NormalGL.png'))


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
direct_light.set_pos(0, -10, 10)
direct_light.look_at(0, 0, 0)


def rotate_card(task):
    card_np.set_p(-22.5 + sin(task.time / 3.0) * 5.0)
    card_np.set_h(cos(task.time / 3.0) * 5.0)
    return task.cont
base.taskMgr.add(rotate_card)

base.run()
