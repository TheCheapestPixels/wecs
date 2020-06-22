"""
Boilerplate code to run a WECS-based game. A game's typical ``main.py``
looks like this:

.. code-block:: python

   #!/usr/bin/env python
   
   import os
   
   from wecs import boilerplate
   
   
   if __name__ == '__main__':
       boilerplate.run_game(
           console=True,
           keybindings=True,
           module_name=os.path.dirname(__file__),
       )

To write your game, implement the module ``game`` (either in a 
``game.py`` or ``game/__init__.py``), 

"""

import sys

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.core import System
from wecs.panda3d import ECSShowBase


def run_game(module_name=None, simplepbr=False, simplepbr_kwargs=None, console=False, keybindings=False,
             debug_keys=False):
    """
    This function...

    - starts a Panda3D instance
    - sets it up for use with WECS
    - imports the module ``game``
    - adds systems of types specified in ``game.system_types`` (if
      present) to ``base.ecs_world``,
    - runs Panda3D's main loop.


    :param simplepbr: Initialize ``panda3d-simplepbr``.
    :param simplepbr_kwargs: key word argument to pass to 
        ``simplepbr.init()`` (if :param simplepbr: is True.) 
    :param console: Set up the CEF-based console
        (``panda3d-cefconsole``).
    :param keybindings: Set up ``panda3d-keybindings`` listener.
    :param module_name: Passed as ``config_module`` to the keybinding
        listener's ``add_device_listener``.
    :param debug_keys: The boilerplate will use Panda3D's key press
        events to make four functions available:

        - ``Escape``: Close the application by calling ``sys.exit()``.
        - ``F9``: open / close the CEF console (if present).
        - ``F10``: show / hide the frame rate meter.
        - ``F11``: Start a ``pdb`` session in the underlying terminal.
        - ``F12``: Connect to ``pstats``.
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
    import game  
    # system_types is deprecated, because badly named. Do not use.
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
