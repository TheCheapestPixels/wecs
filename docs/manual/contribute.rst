Contributing to WECS
====================

WECS is in very early dev phase, and we’d love an ysupport we can get.

Coding
------

Feel fre to fork the project, play and expand upon it. Have a look at
the TODO page.

The current devs hang out at `this channel on
discord <https://discord.com/channels/722508679118848012/722510686474731651>`__.

Documentation
-------------

*WECS* documentation is made of two sources: - a set of .md files
residing in the ``/manual/`` folder, describing the system. and - the
docstrings in the code that generate the API Reference section

The .md files are translated to .rst files and than uploaded to
https://wecs.readthedocs.io/

Generating the docs
~~~~~~~~~~~~~~~~~~~

To generate docs you should simply run ``./gen.sh`` from the /doc
directory. This generates the needed files and the resulting html.

Requirements
^^^^^^^^^^^^

You’ll need the ``pandoc`` conversion utility to be installed.
