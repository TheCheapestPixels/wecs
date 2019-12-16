# Tiny functions that should be built-in but aren't.

def clamp(n, floor, ceiling):
    return max(floor, min(n, ceiling))

def snap_vector(vec, snap):
    for v, vector in enumerate(vec):
        vec[v] = round(vector/snap)*snap
    return vec
