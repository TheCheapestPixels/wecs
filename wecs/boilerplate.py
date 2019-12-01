import sys

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.panda3d import ECSShowBase as ShowBase


def run_game(simplepbr=False, simplepbr_kwargs=None, console=True):
    # Application Basics
    ShowBase()
    base.win.setClearColor((0.5,0.7,0.9,1))
    base.disable_mouse()
    if simplepbr is True:
        import simplepbr
        if simplepbr_kwargs is None:
            simplepbr_kwargs = {}  # i.e. dict(max_lights=1)
        simplepbr.init(**simplepbr_kwargs)

    # Handy Helpers:
    # esc: quit
    # f 9: console
    # f10: frame rate meter
    # f11: pdb, during event loop
    # f12: pstats; connects to a running server
    base.accept('escape', sys.exit)

    if console:
        base.console_open = False
        base.console = make_console()
        base.console.node().hide()
        def toggle_console():
            base.console_open = not base.console_open
            if base.console_open:
                base.console.node().show()
            else:
                base.console.node().hide()
        base.accept('f9', toggle_console)

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


def make_console():
        import cefpanda

        console = cefpanda.CEFPanda(size=[-1, 1, 0, 1])
        def console_handler(entry):
            # Do stuff and report back into the console
            # I'm just looping this back here for demo purposes
            result = entry
            console.exec_js_func('python_result', result)
        console.set_js_function('call_python', console_handler)
        console.load_file('ui/console.html')
        return console
