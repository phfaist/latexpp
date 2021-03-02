List of fixes
-------------

Here is a list of all "fixes" that you can apply to your latex document.

Each class corresponds to a fix that you can list in your ``fixes:`` section of
your ``lppconfig.yml`` file.  See :ref:`howtouse` and :ref:`lppconfig`.

Arguments indicated in parentheses are provided by corresponding YAML keys in
the ``lppconfig.yml`` config file.  For instance, the instruction

.. code-block:: yaml

   fixes:
     ...
     - name: 'latexpp.fixes.figures.CopyAndRenameFigs'
       config:
         # template name for figure output file name
         fig_rename: '{fig_counter:02}-{orig_fig_basename}{fig_ext}'
         # start at figure # 11
         start_fig_counter: 11
     ...

translates to the fix instantiation (python class)::

  latexpp.fixes.figures.CopyAndRenameFigs(
      fig_rename="{fig_counter:02}-{orig_fig_basename}{fig_ext}",
      start_fig_counter=11
  )


.. contents:: Categories of Fixes:
   :local:

   

General document contents & formatting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.input.EvalInput

.. autoclass:: latexpp.fixes.comments.RemoveComments

Expanding custom macros
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.newcommand.Expand

.. autoclass:: latexpp.fixes.macro_subst.Subst

Tweaking document contents
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.environment_contents.InsertPrePost

.. autoclass:: latexpp.fixes.ifsimple.ApplyIf

References and citations
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.ref.ExpandRefs

.. autoclass:: latexpp.fixes.labels.RenameLabels

.. autoclass:: latexpp.fixes.bib.CopyAndInputBbl

.. autoclass:: latexpp.fixes.bib.ApplyAliases

Figures
~~~~~~~

.. autoclass:: latexpp.fixes.figures.CopyAndRenameFigs

Preamble, packages, local files, and other dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.usepackage.CopyLocalPkgs

.. autoclass:: latexpp.fixes.usepackage.RemovePkgs

.. autoclass:: latexpp.fixes.preamble.AddPreamble

.. autoclass:: latexpp.fixes.deps.CopyFiles

Act on parts of your document
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.regional_fix.Apply

Create archive with all files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.archive.CreateArchive


Package-specific fixes
~~~~~~~~~~~~~~~~~~~~~~

These fix classes expand the definitions that are provided by a given package in
order to remove the dependency of a document on that package.

.. autoclass:: latexpp.fixes.pkg.cleveref.ApplyPoorMan

.. autoclass:: latexpp.fixes.pkg.phfqit.ExpandQitObjects

.. autoclass:: latexpp.fixes.pkg.phfqit.ExpandMacros

.. autoclass:: latexpp.fixes.pkg.phfthm.Expand

.. autoclass:: latexpp.fixes.pkg.phfparen.Expand

