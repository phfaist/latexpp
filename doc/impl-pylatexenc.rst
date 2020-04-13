
.. _implementation-notes-pylatexenc:

Implementation notes for `pylatexenc` usage
===========================================

We use `pylatexenc` to parse the latex code into a data structure of nodes.  See
https://pylatexenc.readthedocs.io/en/latest/latexwalker for more information.

There is a small API difference however between `pylatexenc` and `latexpp`
regarding how to get the latex code associated with a node.

.. note::

   The following remark below addresses how to get the raw latex code associated
   with a node.  Within a fix's :py:func:`~latexpp.fix.BaseFix.fix_node()`
   method, however, you should probably be using
   :py:func:`~latexpp.fix.BaseFix.preprocess_contents_latex()` or
   :py:func:`~latexpp.fix.BaseFix.preprocess_latex()` instead, which also ensure
   that the fix is applied recursively to argument nodes and to children nodes.

   If you use the `node.to_latex()` method discussed below, it's up to you to
   ensure that the fix is properly applied to all children nodes as well.

With `pylatexenc.latexwalker`, each node class has a `latex_verbatim()` method
that returns the piece of the original string that that node represents.  But
because here we're changing the node properties, we need to actually recompose
the latex code from the updated node properties.  That is, if we used
`node.latex_verbatim()`, then the result would not actually reflect any changes
made to the node properties such as macro name or arguments.

The solution that `latexpp` introduced is to use a special, internal
:py:class:`~pylatexenc.latexwalker.LatexWalker` subclass that tags on all nodes
an additional method `to_latex()` that recomposes the latex code associated with
the node, directly from the node attributes.  This way, calling
`node.to_latex()` is guaranteed to use the up-to-date information from the node
attributes.

In an effort to avoid bugs, the method `node.latex_verbatim()` is disabled and
will throw an error.  Simply use `node.to_latex()` instead.

**TL;DR**: use `node.to_latex()` instead of `node.latex_verbatim()`.  But you
should probably be using
:py:func:`~latexpp.fix.BaseFix.preprocess_contents_latex()` anyway.
