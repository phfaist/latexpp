Latexpp Pragmas
---------------

Pragmas are special comments in your LaTeX document that influence how `latexpp`
processes your document.

There is currently only a single pragma that is built into `latexpp`: the `skip`
pragma.  Other pragms have to be enabled by specific fixes.


The `skip` built-in pragma
~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest example—and perhaps the most useful
pragma—is the one that instructs `latexpp` to skip a section of code entirely:

.. code-block:: latex

   ...
   %%!lpp skip {
   \def\someComplexCommand#1that latexpp{%
     \expandafter\will\never{be able to parse}%
     correctly}
   %%!lpp }
   ...

General pragma syntax
~~~~~~~~~~~~~~~~~~~~~

A simple pragma has the syntax:

.. code-block:: latex

   ...
   %%!lpp pragma arguments
   ...

where `pragma` is a pragma name and `arguments` are further information that can
be provided to whatever fix parses the pragma.  The pragma must start with the
exact string ``%%!lpp``: two percent signs (the first initiating the LaTeX
comment), an exclamation mark, and the letters ``lpp`` in lowercase with no
spaces between these components.  The entire pragma instruction must be on one
line.  The pragma name is separated from ``%%!lpp`` by whitespace. Any arguments
are processed like a shell command line: Arguments are separated by spaces and
can be quoted using single or double quotes (we use :py:class:`~shlex.shlex` to
split the the argument list).

A scoped pragma has the syntax:

.. code-block:: latex

   ...
   %%!lpp pragma arguments {
   ...
   %%!lpp }
   ...

The pragma instruction is exactly the same as for a simple pragma, except that
it must finish with an opening brace character '{' separated by whitespace from
the rest of the pragma instruction.  (Trailing whitespace after the brace is
ignored.)  The scope is closed using a ``%%!lpp`` marker as for a simple pragma,
whitespace, and a closing brace.

To write a custom fix that parses pragmas, see :ref:`customfix`.


Other pragmas associated with specific fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See fixes:

  - :py:class:`latexpp.fixes.regional_fix.Apply`.

  - more might come in the future!





