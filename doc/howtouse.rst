.. _howtouse:

How to use *latexpp*
--------------------

The latex preprocessor ``latexpp`` reads your main latex document and copies it
to an output directory while applying a series of "fixes" that you can
configure.  For instance, you can remove comments, you can include files that
you input with ``\input`` macros, or you can replace custom macros by their
LaTeX expansion.

You run ``latexpp`` in a folder with a ``lppconfig.yml`` file that specifies the
necessary information such as the main LaTeX document, the output directory, and
which fixes to apply.


.. contents:: Contents:
   :local:


Sample ``lppconfig.yml``
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

  # latexpp config for MyDocument.tex
  #
  # This is YAML syntax -- google "YAML tutorial" to get a quick intro.
  # Be careful with spaces since indentation is important.

  # the master LaTeX document -- this file will not be modified, all
  # output will be produced in the output_dir
  fname: 'MyDocument.tex'

  # output file(s) will be created in this directory, originals will
  # not be modified
  output_dir: 'latexpp_output'
  
  # main document file name in the output directory
  output_fname: 'paper.tex'
  
  # specify list of fixes to apply, in the given order
  fixes:

    # replace \input{...} directives by the contents of the included
    # file
    - 'latexpp.fixes.input.EvalInput'
  
    # remove all comments
    - 'latexpp.fixes.comments.RemoveComments'

    # copy any style files (.sty) that are used in the document and
    # that are present in the current directory to the output directory
    - 'latexpp.fixes.usepackage.CopyLocalPkgs'
  
    # copy figure files to the output directory and rename them
    # fig-01.xxx, fig-02.xxx, etc.
    - 'latexpp.fixes.figures.CopyAndRenameFigs'

    # Replace \bibliography{...} by \input{xxx.bbl} and copy the bbl
    # file to the output directory.  Make sure you run (pdf)latex on
    # the main docuemnt before running latexpp
    - 'latexpp.fixes.bib.CopyAndInputBbl'
  
    # Expand some macros. Latexpp doesn't parse \newcommand's, so you
    # need to specify here the LaTeX code that the macro should be
    # expanded to. If the macro has arguments, specify the nature of
    # the arguments here in the 'argspec:' key (a '*' is an optional
    # * character, a '[' one optional square-bracket-delimited
    # argument, and a '{' is a mandatory argument). The argument values
    # are available via the placeholders %(1)s, %(2)s, etc. Make sure
    # to use single quotes for strings that contain \ backslashes.
    - name: 'latexpp.fixes.macro_subst.Subst'
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


Config File Syntax
~~~~~~~~~~~~~~~~~~

The config file follows standard YAML syntax (if you're in doubt, google a YAML
tutorial).

See the ``latexpp/fixes/`` directory for the list of possible fixes.  There
isn't any good documentation at the moment (I wrote this preprocessor in the
matter of a few days, and I won't have tons of time to devote to it). But the
python source is pretty short and should be relatively decipherable.

Each fix is specified by a qualified python class name.  For instance,
``latexpp.fixes.comments.RemoveComments`` invokes class ``RemoveComments`` from
the python module ``latexpp.fixes.comments``.  You can specify custom arguments
to the class constructor by using the syntax with the 'name:' and 'config:' keys
as shown above.  The keys in each 'config:' section are directly passed on to
the class constructor as corresponding keyword arguments.

The fixes in the ``latexpp/fixes/pkg/`` directory are those fixes that are
supposed to apply all definitions of the corresponding package in order to
remove a dependency on that package.

It's also straightforward to write your own fix classes to do more complicated
stuff.  Create a python package (a new folder ``mypackage`` with an empty
``__init__.py`` file) and create a python module (e.g. ``myfixmodule.py``) in
that package that defines your fix class (e.g. ``MyFix``).  You can get
inspiration from one of the simple examples in the ``latexpp/fixes/`` folder.
Set up your ``$PYTHONPATH`` so that your python package is exposed to python.
Then simply specify the pacakge/module your fix is located in in the YAML file,
e.g., ``mypackage.myfixmodule.MyFix`` instead of
``latexpp.fixes.xxxxx.YYYY``.


Common pitfalls
~~~~~~~~~~~~~~~

* **Errors in the document preamble:**

  Beacuse the LaTeX parser is not a full LaTeX engine and parses the document
  contents basically like a markup language, the parser may choke on preamble
  definitions that e.g.  define new macros.  These definitions are best placed
  in a separate custom package.  Simply create a file called 'mymacros.sty' that
  starts with the line::

    \ProvidesPackage{./mymacros}
    
    ...

  and then use this in the main document as::

    \usepackage{./mymacros}

  Added benefit: You don't need ``\makeatletter`` in the `*.sty` file, because
  latex style files automatically ``\makeatletter`` enabled.

* ...?
