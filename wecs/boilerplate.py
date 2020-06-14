"""
A panda3D boilerplate.

TODO rename to panda3D_boilerplate
"""
import sys

from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.core import System
from wecs.panda3d import ECSShowBase


def run_game(module_name=None, simplepbr=False, simplepbr_kwargs=None, console=False, keybindings=False,
             debug_keys=False):
    """
    Runs the game by using the panda3D's main run loop.
    It also sets up several handy keyboard shortcuts to use while deveoping:
    esc: quit
    F9 : show/hide console
    F10: show/hide frame rate meter
    F11: debug using pdb, during event loop
    F12: pstats; connects to a running server

    :param module_name:
    :param simplepbr:
    :param simplepbr_kwargs:
    :param console:
    :param keybindings:
    :param debug_keys:

    """
    # Application Basics
    ECSShowBase()
    sky_color = (0.3, 0.5, 0.95, 1)
    base.win.setClearColor(sky_color)
    base.disable_mouse()

    if keybindings:
        from keybindings.device_listener import add_device_listener
        from keybindings.device_listener import SinglePlayerAssigner
        add_device_listener(
            config_module=module_name,
            config_file="keybindings.toml",
            debug=True,
            assigner=SinglePlayerAssigner(),
        )
    if simplepbr is True:
        import simplepbr
        if simplepbr_kwargs is None:
            simplepbr_kwargs = {}  # i.e. dict(max_lights=1)
        simplepbr.init(**simplepbr_kwargs)

    if console:
        from cefconsole import add_console
        from cefconsole import PythonSubconsole
        # FIXME next check looks redundant. cefconsole uses F9 as default,
        # FIXME and it's activated even if debug_keys false
        if debug_keys:

            add_console(subconsoles=[PythonSubconsole()], toggle="f9")
        else:
            add_console(subconsoles=[PythonSubconsole()])

    if debug_keys:
        base.accept('escape', sys.exit)
        base.frame_rate_meter_visible = False
        base.set_frame_rate_meter(base.frame_rate_meter_visible)

        def toggle_frame_rate_meter():
            base.frame_rate_meter_visible = not base.frame_rate_meter_visible
            base.set_frame_rate_meter(base.frame_rate_meter_visible)

        base.accept('f10', toggle_frame_rate_meter)

        def debug():
            import pdb
            pdb.set_trace()

        base.accept('f11', debug)

        def pstats():
            base.pstats = True
            PStatClient.connect()

        base.accept('f12', pstats)

    # Set up the world:
    import game  # fixme this assumes that module game exists. That's a strong undocumented requirement.
    # system_types is deprecated, because badly named. Do not use.
    # fixme if above comment is true, than it should be fixed. Too early for keeping "backward compatibility" stuff(?)
    if hasattr(game, 'system_types'):
        add_systems(game.system_types)
    if console:
        base.console.render_console()

    # And here we go...
    base.run()


def add_systems(system_specs):
    """
    Register additional systems to the world.
    Registered systems will be activated in every update.

    :param system_specs:
    :return:
    """
    sort, priority = 1, 1

    for spec in system_specs:
        # Figure out the full_specs
        if isinstance(spec, System):
            system = spec
            priority -= 1
        elif issubclass(spec, System):
            system = spec()
            priority -= 1
        else:
            sort, priority, system_spec = spec
            if isinstance(system_spec, System):
                system = system_spec
            elif issubclass(system_spec, System):
                system = system_spec()
            else:
                raise ValueError

        base.add_system(system, sort, priority=priority)
