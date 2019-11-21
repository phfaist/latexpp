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

   

General fixes — document contents & formatting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.input.EvalInput

.. autoclass:: latexpp.fixes.comments.RemoveComments

.. autoclass:: latexpp.fixes.macro_subst.Subst

General fixes — used packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.usepackage.RemovePkgs

.. autoclass:: latexpp.fixes.usepackage.CopyLocalPkgs

General fixes — preamble definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.preamble.AddPreamble

.. autoclass:: latexpp.fixes.deps.CopyFiles

General fixes — figures
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.figures.CopyAndRenameFigs

General fixes — bibliography
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.bib.CopyAndInputBbl

.. autoclass:: latexpp.fixes.bib.ApplyAliases

General fixes — act on parts of your document
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.regional_fix.Apply


General fixes — create archive with all files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.archive.CreateArchive


Expand package macros
~~~~~~~~~~~~~~~~~~~~~

These fix classes expand the definitions that are provided by a given package in
order to remove the dependency of a document on that package.

.. autoclass:: latexpp.fixes.pkg.cleveref.ApplyPoorMan

.. autoclass:: latexpp.fixes.pkg.phfqit.ExpandQitObjects

.. autoclass:: latexpp.fixes.pkg.phfqit.ExpandMacros

.. autoclass:: latexpp.fixes.pkg.phfthm.Expand

.. autoclass:: latexpp.fixes.pkg.phfparen.Expand

