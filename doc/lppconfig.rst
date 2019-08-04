The ``lppconfig.yml`` configuration file
----------------------------------------

The ``lppconfig.yml`` file is placed in the current working directory where your
main original LaTeX document is developed.  It specifies how to process the
document and "fix" it, and where to output the "fixed" version.

See :ref:`howtouse` for a sample ``lppconfig.yml`` file.

The ``lppconfig.yml`` file is a YAML file.  `Google "YAML tutorial"
<https://www.google.com/search?q=YAML+tutorial>`_ to get an idea.  It's
intuitive and easy to read.  In ``lppconfig.yml`` you define the necessary
information to run `latexpp` on a latex document.

``lppconfig.yml`` file structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

using the following fields that are specified at
the root level of the file:

- `fname: <main-LaTeX-document-file-name>` — specifies the master LaTeX document
  that you would like to process.

  If your LaTeX document includes content from other LaTeX files with ``\input``
  or ``\include`` commands, then you need to specify the master document here.
  Make sure you use a fix like :py:class:`latexpp.fixes.input.EvalInput` to
  follow ``\input`` directives.

  If there are different documents that you would like to process independently,
  then you should use different ``lppconfig.yml`` files.  You can either place
  the documents in separate directories with their corresponding
  ``lppconfig.yml`` files, or you can name the config files
  ``lppconfig-mydoc1.yml``, ``lppconfig-myotherdoc.yml`` and then run
  `latexpp -p mydoc1` or `latexpp -p myotherdoc` to run `latexpp` using the
  corresponding settings.

- `output_dir: <output-directory-name>` — where to write the output files.  This
  should be a nonexisting directory in which the preprocessed latex document is
  written (along with possible dependencies depending on the fixes that were
  invoked).

- `output_fname: <file-name>` — how to name the main latex document in the
  output directory.

- `fixes: <list of fixes>` — a list of which fixes to apply with a corresponding
  configuration.  See below.

Specifying the fixes
~~~~~~~~~~~~~~~~~~~~

With the `fixes:` key you specify a list of fixes and the corresponding
configuration:

.. code-block:: yaml

   fixes:
   - <fix-spec-1>
   - <fix-spec-2>
   ...

Each `<fix-spec-N>` must be either a string or a dictionary.  If `<fix-spec-N>`
is a string, then it is the fully qualified python name of the fix class, such
as ``latexpp.fixes.figures.CopyAndRenameFigs``, in which case the fix is invoked
without specifying a custom configuration.  If it is a dictionary,
`<fix-spec-N>` should have the following structure:

.. code-block:: yaml

   name: <qualified-python-fix-class>
   config:
     <config-key-1>: <config-value-1>
     <config-key-2>: <config-value-2>

where `<qualified-python-fix-class>` is the fully qualified python name of the
fix class, such as ``latexpp.fixes.figures.CopyAndRenameFigs``.  The fix class
will be invoked with the given configuration.  Namely, the fix class will be
instantiated with the given key-value pairs as constructor arguments.

You should check the documentation of the individual fix classes to see what
arguments they accept.  Arguments to fix class constructors are always passed as
keyword arguments.
