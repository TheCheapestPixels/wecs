#!/usr/bin/env python

import sys

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.panda3d import ECSShowBase as ShowBase
# import simplepbr


if __name__ == '__main__':
    # Application Basics
    ShowBase()
    #simplepbr.init(max_lights=1)
    base.disable_mouse()

    # Handy Helpers: esc to quit, f11 for pdb, f12 for pstats
    base.accept('escape', sys.exit)
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
