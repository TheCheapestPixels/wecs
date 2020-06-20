Contributing to WECS
====================

WECS is currently in the alpha stage of development, closing in on beta.
That means that while most major features have been put into place, and
the viability of WECS has been shown, there are still some essential
features missing, and many, many rough edges remain to be smoothed out.
We would love any support we can get.

Feel free to fork the project, play around with it, expand it, and build
games an applications on top of it. Any problem that you encounter, or
question that comes up and is not answered by the manual, is an edge
that needs to be sanded down. Please report it, or fix it and submit a
pull request.

Code
----

WECS has a rather long TODO list. If you feel like tackling any task, or
adding other features that you feel are missing, have at it.

Style Guide
~~~~~~~~~~~

Our style guideline is

-  PEP8 with a line length limit of “72 would be preferrable, up to 100
   are justifiable.”
-  Symbolic strings (constants, file names, etc.) are in single quotes,
   strings for human consumption in double quotes.

Since we are ad-hoc-ing our style a lot, this manual section also needs
to be elaborated on.

Documentation
-------------

WECS’ documentation comes from two sources:

-  a set of Markdown files, namely the ``README.md``, and additional
   manual files residing in ``docs/manual/``,
-  the docstrings in the code from which the API Reference is generated.

Generating the documentation has following requirements:

-  The Python packages ``sphinx``, ``sphinx-autoapi``, and
   ``sphinx_rtd_theme``.
-  ``pandoc``, which is *not* a Python package, and has to be installed
   via your operating system’s package manager.

To generate the documentation, change to WECS’ ``docs/`` directory and
run ``./gen.sh``. This will…

-  copy ``README.md`` into the ``docs/manual/readme.md``,
-  use ``pandoc`` to convert the ``.md`` files in ``docs/manual/`` to
   ``.rst``,
-  generate the documentation with Sphinx.

The generated documentation can be found in ``docs/_build``. The HTML
document starts with ``_build/html/index.html``.

.. _style-guide-1:

Style Guide
~~~~~~~~~~~

Markdown documentation style:

-  There are two empty lines before a headline (except for the one
   starting a document), except between consecutive headlines, between
   which there is one empty line.

   .. code:: text

      Manual Page
      -----------

      Chapter One
      -----------

      Lorem Ipsum and so on...


      Chapter Two
      -----------

      ... ti amat.

-  Lines are no longer than 72 characters for easier display on half a
   screen. Things like links are exempted.

   .. code:: text

               1         2         3         4         5         6         7
      123456789012345678901234567890123456789012345678901234567890123456789012
      This is the line that doesn't end; Yes, it goes on and on, my friend.
      Some dev guy started writing it not knowing what it was, and he'll
      continue writing it forever just because
      [this is the line that doesn't end...](https://www.youtube.com/watch?v=xz6OGVCdov8)

-  There are no comments in Markdown.
