List of fixes
-------------

Here is a list of all "fixes" that you can apply to your latex document.

.. contents:: Categories of Fixes:
   :local:

   

General fixes
~~~~~~~~~~~~~

.. autoclass:: latexpp.fixes.preamble.AddPreamble

.. autoclass:: latexpp.fixes.comments.RemoveComments

.. autoclass:: latexpp.fixes.usepackage.RemovePkgs

.. autoclass:: latexpp.fixes.usepackage.CopyLocalPkgs

.. autoclass:: latexpp.fixes.deps.CopyFiles

.. autoclass:: latexpp.fixes.figures.CopyAndRenameFigs

.. autoclass:: latexpp.fixes.input.EvalInput

.. autoclass:: latexpp.fixes.bib.CopyAndInputBbl

.. autoclass:: latexpp.fixes.bib.ApplyAliases

.. autoclass:: latexpp.fixes.macro_subst.Subst

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

