octaves = 2

vdata = GeomVertexData('name', format, Geom.UHStatic)
vdata.setNumRows(4)

vertex = GeomVertexWriter(vdata, 'vertex')
color = GeomVertexWriter(vdata, 'color')

vertex.addData3(1, 0, 0)
color.addData4(0, 0, 1, 1)
