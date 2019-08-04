How *latexpp* works
-------------------

The ``latexpp`` preprocessor relies on `pylatexenc 2.0
<https://github.com/phfaist/pylatexenc>`_ to parse the latex document into an
internal node structure.  For instance, the chunk of latex code::
  
  Hello, \textit{world}! % show a greeting

will be parsed into a list of four nodes, a ‘normal characters node’ ``"Hello,
"``, a ‘macro node’ ``\textit`` with argument a ‘group node’ ``{world}`` which
itself contains a ‘normal characters node’ ``world``, a ‘normal characters node’
``"! "``, and a ‘latex comment node’ ``% show a greeting``.  The structure is
recursive, with e.g. macro arguments and environment contents themselves
represented as nodes which can contain further macros and environments.  See
`pylatexenc.latexwalker
<https://pylatexenc.readthedocs.io/en/latest/latexwalker/>`_ for more
information.  The `pylatexenc` library has a list of some known macros and
environments, and knows how to parse their arguments.  Some fixes in `latexpp`
add their own macro and environment definitions.

Once the latex document is parsed into the node structure, then the nodes are
traversed recursively including macro arguments and environment contents.  For
each node, we query all the fixes in the specified order to see if that return a
latex representation of the given node.  If no fix is found, then the original
latex representation of the node is retained.
