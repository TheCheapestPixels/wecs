import sys
import inspect

from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.core import System
from wecs.panda3d import ECSShowBase as ShowBase


def run_game(module_name=None, simplepbr=False, simplepbr_kwargs=None, console=False, keybindings=False, debug_keys=False):
    # Application Basics
    ShowBase()
    base.win.setClearColor((0.5,0.7,0.9,1))
    base.disable_mouse()

    if keybindings:
        import os
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

    # Handy Helpers:
    # esc: quit
    # f 9: console
    # f10: frame rate meter
    # f11: pdb, during event loop
    # f12: pstats; connects to a running server

    if console:
        from cefconsole import add_console
        from cefconsole import PythonSubconsole
        if debug_keys:
            add_console(subconsoles=[PythonSubconsole()], toggle="f9")
        else:
            add_console(subconsoles=[PythonSubconsole()])

    if debug_keys:
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
    if hasattr(game, 'system_types'):
        add_systems(game.system_types)
    if console:
        base.console.render_console()

    # And here we go...
    base.run()


def add_systems(system_specs):
    def is_bare_type(spec): return inspect.isclass(spec) and issubclass(spec, System)
    def is_bare_system(spec): return isinstance(spec, System)
    def is_spec_with_sort(spec):
        if not isinstance(spec, (tuple, list)):
            return False
        if not len(spec) == 2:
            return False
        if not isinstance(spec[0], int):
            return False
        if not (is_bare_type(spec[1]) or is_bare_system(spec[1])):
            return False
        return True
    def is_spec_with_both(spec):
        if not isinstance(spec, (tuple, list)):
            return False
        if not len(spec) == 3:
            return False
        if not isinstance(spec[0], int):
            return False
        if not isinstance(spec[1], int):
            return False
        if not (is_bare_type(spec[2]) or is_bare_system(spec[2])):
            return False
        return True
        
    def task_sort(task_dict):
        sorts = sorted(task_dict.keys(), key=lambda t: (t[0],-t[1]))
        wecs_sorted = [
            (wecs_sort, p3d_sort, p3d_priority, task_dict[(p3d_sort, p3d_priority)])
            for wecs_sort, (p3d_sort, p3d_priority) in enumerate(sorts)
        ]
        return wecs_sorted

    sort, priority = 0, 0
    full_specs = {}  # (sort, priority): system_instance
    # Figure out the full_specs
    for spec in system_specs:
        if is_bare_type(spec):
            system = spec()
        elif is_bare_system(spec):
            system = spec
        elif is_spec_with_sort(spec):
            sort, system_spec = spec
            if is_bare_type(system_spec):
                system = system_spec()
            else:
                system = system_spec
            priority = 0
        elif is_spec_with_both(spec):
            sort, priority, system_spec = spec
            if is_bare_type(system_spec):
                system = system_spec()
            else:
                system = system_spec
        else:
            # Can't interpret a system spec.
            raise ValueError(spec)
        assert (sort, priority) not in full_specs.keys()
        full_specs[(sort, priority)] = system
        priority -= 1

    sort_spec = task_sort(full_specs)
    for (wecs_sort, p3d_sort, p3d_priority, system) in sort_spec:
        base.add_system(system, wecs_sort, p3d_sort, p3d_priority)
