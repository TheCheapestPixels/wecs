#!/usr/bin/env python

import os

from wecs import boilerplate


if __name__ == '__main__':
    boilerplate.run_game(
        keybindings=True,
        simplepbr=True,
        simplepbr_kwargs=dict(
            msaa_samples=1,
            max_lights=8,
            use_emission_maps=True,
            use_occlusion_maps=True,
            use_normal_maps=False,  # FIXME: get a GPU that can do this
            enable_shadows=False,  # FIXME: get a GPU that can do this
        ),
    )
