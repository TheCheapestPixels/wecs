import sys

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.panda3d import ECSShowBase as ShowBase


def run_game(simplepbr=False, simplepbr_kwargs=None):
    # Application Basics
    ShowBase()
    base.disable_mouse()
    if simplepbr is True:
        import simplepbr
        if simplepbr_kwargs is None:
            simplepbr_kwargs = {}  # i.e. dict(max_lights=1)
        simplepbr.init(**simplepbr_kwargs)

    # Handy Helpers: esc to quit, f11 for pdb, f12 for pstats
    base.accept('escape', sys.exit)
    base.frame_rame_meter_visible = False
    base.set_frame_rate_meter(base.frame_rame_meter_visible)
    def toggle_frame_rate_meter():
        base.frame_rame_meter_visible = not base.frame_rame_meter_visible
        base.set_frame_rate_meter(base.frame_rame_meter_visible)
    base.accept('f10', toggle_frame_rate_meter)
    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)
    def pstats():
        base.pstats = True
        PStatClient.connect()
    base.accept('f12', pstats)

    # Set up the world:
    import game
    for sort, system_type in enumerate(game.system_types):
        base.add_system(system_type(), sort)

    # And here we go...
    base.run()
