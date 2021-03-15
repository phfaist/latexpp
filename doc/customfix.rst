
.. _customfix:

Writing a custom fix
--------------------

It is easy to write new fixes to integrate them in your `latexpp` flow.  A fix
instance simply performs actions on the document structure in an internal
representation with data nodes, and alters them, removes selected nodes or
produces new nodes that change the LaTeX code of the document.

Quick start
~~~~~~~~~~~

Say you have a LaTeX document that you'd like to process with `latexpp`, and say
that you feel the need to write a particular fix for this document.  Let's try
to get you started in 30 seconds.

In the document's folder, create a new folder which we'll call here ``myfixes``
(this is your fix python package folder, you can give it any valid python
package name).  In that folder, create an empty file called ``__init__.py``.
Finally, create your fix python file, say ``mycustomfix.py``, in that folder and
paste in there the following contents:

.. literalinclude:: example_custom_fix/myfixes/mycustomfix.py

You can then use your new fix by adding to your ``lppconfig.yml``:

.. code-block:: yaml

   ...
   fixes:
     ...
     - name: 'myfixes.mycustomfix.MyGreetingFix'
       config:
         greeting: "I've been expecting you, %(name)s."

In this way, whenever your document contains a macro instruction such as:

.. code-block:: latex

   \greet{Mr. Bond}

it gets replaced by:

.. code-block:: latex

   \emph{I've been expecting you, Mr. Bond.}

To complete your quick start, here are some key points.

Key points
~~~~~~~~~~

- Any configuration items specified in ``config:`` in your ``lppconfig.yml``
  file are passed directly as arguments to the fix class constructor.  You can
  specify booleans, ints, strings, or even full data structures, all using
  standard YaML syntax.

- Your fix class should inherit :py:class:`latexpp.fix.BaseFix`.  You can check
  out the documentation of that class for various utilities you can make use of
  in your fix. (It can also inherit from
  :py:class:`latexpp.fix.BaseMultiStageFix`, see further below.)

- Perform transformations in the document by reimplementing the
  :py:meth:`~latexpp.fix.BaseFix.fix_node()` method.  The argument is a "node"
  in the document structure.  The node is one of `pylatexenc`'s
  :py:class:`~pylatexenc.latexwalker.LatexNode` document node subclasses (e.g.,
  :py:class:`~pylatexenc.latexwalker.LatexMacroNode`).
  (See also :ref:`implementation-notes-pylatexenc`.)

- Make sure you always preprocess all child nodes such as macro arguments, the
  environment body, etc. so that fixes are also applied to them.  As a general
  rule, whenever `fix_node()` returns something different than `None` then it is
  also responsible for applying the fix to all the child nodes of the current
  node as well.  This can be done conveniently with
  :py:meth:`self.preprocess_contents_latex()
  <latexpp.fix.BaseFix.preprocess_contents_latex>` and
  :py:meth:`self.preprocess_latex() <latexpp.fix.BaseFix.preprocess_latex>`
  which directly return LaTeX code that can be inserted in your new replacement
  LaTeX code.

- The parser will assume that a macro does not take any arguments, unless the
  parser is told in advance about that macro.  The parser already knows about a
  set of standard latex macros (e.g., ``\emph``, ``\textbf``, etc.).  Specify
  futher macros with their argument signatures by reimplementing the
  :py:meth:`specs() <latexpp.fix.BaseFix.specs>` method.  (See the doc for
  :py:meth:`specs() <latexpp.fix.BaseFix.specs>` for more info.  Also, it never
  hurts to specify a macro, even if it was already defined.)

- If your fix needs multiple passes through the document, you should inherit the
  class :py:class:`latexpp.fix.BaseMultiStageFix` instead of
  :py:class:`~latexpp.fix.BaseFix`.  In this case you can subdivide your fix
  into "stages," which you define by subclassing
  :py:class:`latexpp.fix.BaseMultiStageFix.Stage` for each stage in your fix
  process.  Each stage object is itself a fix (meaning it indirectly inherits
  from :py:class:`~latexpp.fix.BaseFix`) on which you can reimplement
  `fix_node()` etc.  Each stage is run sequentially.  The "parent" fix object
  then manages the stages and can store data that is accessed and modified by
  the different stages.

  See the documentation for :py:class:`~latexpp.fix.BaseMultiStageFix` for more
  details, and check the fix :py:class:`latexpp.fixes.labels.RenameLabels` for
  an example.

- The preprocessor instance, available as ``self.lpp``, exposes some methods that
  cover some common fixes' special needs:

  + to copy a file to the output directory, use :py:meth:`self.lpp.copy_file()
    <latexpp.preprocessor.LatexPreprocessor.copy_file>`;

  + to parse some LaTeX code into nodes, use
    :py:meth:`self.lpp.make_latex_walker()
    <latexpp.preprocessor.LatexPreprocessor.make_latex_walker>` to create a
    LatexWalker instance that will polish the node classes as required by
    `latexpp` internals;

  + see also :py:meth:`~latexpp.preprocessor.LatexPreprocessor.open_file()`,
    :py:meth:`~latexpp.preprocessor.LatexPreprocessor.check_autofile_up_to_date()`,
    :py:meth:`~latexpp.preprocessor.LatexPreprocessor.register_output_file()`,
    and
    :py:meth:`~latexpp.preprocessor.LatexPreprocessor.create_subpreprocessor()`.
