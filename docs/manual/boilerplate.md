Panda3D Boilerplate
===================

Boilerplate for Panda3D
-----------------------

You want to prototype in Panda3D *now*? Good! Here's the `main.py` of
your project:

```bash
#!/usr/bin/env python

from wecs import boilerplate


def run_game():
    boilerplate.run_game()


if __name__ == '__main__':
    run_game()
```

Then write a `game.py` to set up the world, which is `base.ecs_world`.
FIXME: `system_types`

Now run `python main.py`, and you'll be dropped right into your game.

FIXME: Mention wecs_null_project


Integrations
------------

FIXME:
* cefconsole
* keybindings
* simplepbr
* ???