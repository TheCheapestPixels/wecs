# Tiny functions that should be built-in but aren't.
from panda3d.core import LineSegs
from panda3d.core import NodePath


def clamp(n, floor, ceiling):
    return max(floor, min(n, ceiling))

def snap_vector(vec, snap):
    for v, vector in enumerate(vec):
        vec[v] = round(vector/snap)*snap
    return vec

def draw_grid(x_size, y_size, s):
    lines = LineSegs()
    lines.set_color((0,0,0,1))
    offset = s/2
    for x in range(x_size):
        x = (x*s) - offset
        lines.move_to(x, -offset, 0)
        lines.draw_to(x, (y_size*s)-offset, 0)
    for y in range(y_size):
        y = (y*s) - offset
        lines.move_to(-offset, y, 0)
        lines.draw_to((x_size*s)-offset, y, 0)
    grid = NodePath(lines.create())
    return grid
