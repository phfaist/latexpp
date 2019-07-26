latexpp
=======

Latex preprocessor — apply macro definitions, remove comments, and more

How it works
------------

The latex preprocessor ``latexpp`` reads your main latex document and copies it
to an output directory while applying a series of "fixes" that you can
configure.  For instance, you can remove comments, you can include files that
you input with ``\input`` macros, or you can replace custom macros by their
LaTeX expansion.

You run ``latexpp`` in a folder with a ``lppconfig.yml`` file that specifies the
necessary information such as the main LaTeX document, the output directory, and
which fixes to apply.

Sample ``lppconfig.yml``:

.. code-block:: yaml

  # latexpp config for MyDocument.tex
  #
  # This is YAML syntax -- google "YAML tutorial" to get a quick intro.  Careful
  # with spaces, correct indentation is important.

  # the master LaTeX document -- this file will not be modified, all output will
  # be produced in the output_dir
  fname: 'MyDocument.tex'

  # output file(s) will be created in this directory, originals will not be
  # modified
  output_dir: 'latexpp_output'
  
  # specify list of fixes to apply, in the given order
  fixes:

    # remove all comments
    - 'latexpp.fixes.comments.RemoveCommentsFixes'

    # replace \input{...} directives by the contents of the included file
    - 'latexpp.fixes.input.EvalInputFixes'
  
    # copy any style files (.sty) that are used in the document and that
    # are present in the current directory to the output directory
    - 'latexpp.fixes.usepackage.CopyLocalPkgsFixes'
  
    # copy figure files to the output directory and rename them fig-1.xxx,
    # fig-2.xxx, etc.
    - 'latexpp.fixes.figures.CopyNumberFigsFixes'

    # Replace \bibliography{...} by \input{xxx.bbl} and copy the bbl file to the
    # output directory.  Make sure you run (pdf)latex on the main docuemnt
    # before running latexpp
    - 'latexpp.fixes.bib.CopyBblFixes'
  
    # Expand some macros. Instead of trying to infer the exact expansion that
    # (pdf)latex would itself perform, you specify here a custom string that the
    # macro will be expanded to. If the macro has arguments, specify the nature
    # of the arguments here in the 'argspec:' key (a '*' is an optional *
    # character, a '[' one optional square-bracket-delimited argument, and a '{'
    # is a mandatory argument). The argument values are available via the
    # placeholders %(1)s, %(2)s, etc. Make sure to use single quotes for strings
    # that contain \ backslashes.
    - name: 'latexpp.fixes.macro_subst.Fixes'
      config:
        macros:
          # \tr         -->  \operatorname{tr}
          tr: '\operatorname{tr}'
          # \ket{\psi}  -->  \lvert{\psi}\rangle
          ket:
            argspec: '{'
            repl: '\lvert{%(1)s}\rangle'
          # \braket{\psi}{\phi}  -->  \langle{\psi}\vert{\phi}\rangle
          braket:
            argspec: '{{'
            repl: '\langle{%(1)s}\vert{%(2)s}\rangle'

The config file follows standard YAML syntax (if you're in doubt, google a YAML
tutorial).

See the ``latexpp/fixes/`` directory for the list of possible fixes.  There
isn't any good documentation at the moment (I wrote this preprocessor in the
matter of a few days, and I won't have tons of time to devote to it). But the
python source should be short and relatively understandable.

Each `XXXFixes` class in each module provides a fix that you can invoke from the
YAML config file as shown above.  You can specify custom arguments to the class
constructor by using the syntax with the 'name:' and 'config:' keys as shown
above; the keys in each 'config:' section are directly passed on to the class
constructor.

The fixes in the ``latexpp/fixes/pkg/`` directory are those fixes that are
supposed to apply all definitions of the corresponding package in order to
remove a dependency on that package.

It's also straightforward to write your own fix classes to do more complicated
stuff.  Start from one of the simple examples in the ``latexpp/fixes/`` folder.
Put you fix class in a module and set up your ``$PYTHONPATH`` so that the
package/module is exposed to python.  Then simply specify the pacakge/module
your fix is located in in the YAML file, instead of
``latexpp.fixes.xxxxx.XXXFixes``.


How it actually works
---------------------

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


License
-------

\ (C) 2019 Philippe Faist, philippe dot faist <at@at> bluewin dot ch

MIT Licence, see License.txt

