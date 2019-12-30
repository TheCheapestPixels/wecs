#!/usr/bin/env python

import os

from wecs import boilerplate


if __name__ == '__main__':
    boilerplate.run_game(
        os.path.dirname(__file__),
        console=True,
        keybindings=True,
    )
