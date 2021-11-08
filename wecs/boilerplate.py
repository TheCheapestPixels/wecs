"""
Boilerplate code to run a WECS-based game. A game's typical ``main.py``
looks like this:

.. code-block:: python

   #!/usr/bin/env python
   
   import os
   
   from wecs import boilerplate
   
   
   if __name__ == '__main__':
       boilerplate.run_game(
           keybindings=True,
       )

To write your game, implement the module ``game`` (either in a 
``game.py`` or ``game/__init__.py``), 

"""

import sys
import importlib

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.core import System
from wecs.panda3d import ECSShowBase


def run_game(game_module='game', simplepbr=False,
             simplepbr_kwargs=None, keybindings=False,
             debug_keys=False,
             config=None, config_file=None, debug=None, assigner=None):
    """
    This function...

    - starts a Panda3D instance,
    - sets it up for use with WECS,
    - imports the module ``game`` (or whatever name is passed as
      ``game_module``),
    - adds systems of types specified in ``game.system_types`` (if
      present) to ``base.ecs_world``,
    - runs Panda3D's main loop.


    :param game_module: The name of the game module
    :param simplepbr: Initialize ``panda3d-simplepbr``.
    :param simplepbr_kwargs: key word argument to pass to 
        ``simplepbr.init()`` (if :param simplepbr: is True.) 
    :param keybindings: Set up ``panda3d-keybindings`` listener.
    :param debug_keys: The boilerplate will use Panda3D's key press
        events to make four functions available:

        - ``Escape``: Close the application by calling ``sys.exit()``.
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
        dev_lis_args = {}
        if config is not None:
            dev_lis_args.update(dict(config=config))
        if config_file is not None:
            dev_lis_args.update(dict(config_file=config_file))
        if debug is not None:
            dev_lis_args.update(dict(debug=debug))
        if assigner is not None:
            dev_lis_args.update(dict(assigner=assigner))
        else:
            dev_lis_args.update(dict(assigner=SinglePlayerAssigner()))
        add_device_listener(**dev_lis_args)

    if simplepbr is True:
        import simplepbr
        if simplepbr_kwargs is None:
            simplepbr_kwargs = {}  # i.e. dict(max_lights=1)
        simplepbr.init(**simplepbr_kwargs)

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
    game = importlib.import_module(game_module)
    # FIXME: system_types is a bad name, since the allowed specs are now
    # more complicated (see add_systems' code). system_specs would be
    # better.
    if hasattr(game, 'system_types'):
        add_systems(game.system_types)

    # And here we go...
    base.run()


def add_systems(system_specs):
    """
    Registers additional systems to the world. Each system specification
    must be in one of these formats:

    .. code-block:: python
    
       system_types = [
          SystemType,
          system_instance,
          (sort, priority, SystemType),
          (sort, priority, system_instance),
       ]
    
    Each ``SystemType`` is instantiated with no arguments.
    
    ``sort`` and ``priority`` refer to the same parameter's in
    Panda3D's task manager. If they are not provided, a best effort
    guess is made: Starting at sort 1 and priority 0, priority is
    counted down. If the values are provided, then the next system
    for which they are *not* specified will continue counting down
    from the last provided values.

    Registered systems will be activated in every update.

    :param system_specs: An iterable containing system specifications.
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
