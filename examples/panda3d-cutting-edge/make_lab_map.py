from panda3d.core import NodePath
from panda3d.core import CardMaker


cm = CardMaker('card')
cm.set_frame(-31, 31, -31, 31)

map_np = NodePath("map")
card = map_np.attach_new_node(cm.generate())
card.set_p(-90)

for i in range(21):
    sp = map_np.attach_new_node(f'spawn_point_a_{i}')
    sp.set_pos(-30 + i*3, -30, 0)
    sp = map_np.attach_new_node(f'spawn_point_b_{i}')
    sp.set_pos(-30 + i*3, 30, 0)
    sp.set_h(180)


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
