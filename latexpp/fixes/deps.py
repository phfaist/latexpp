
import logging

logger = logging.getLogger(__name__)

from latexpp.fix import BaseFix


class CopyFiles(BaseFix):
    """
    Copies the given files to the output directory.  Use this for dependencies
    that aren't obvious, like a custom LaTeX class.

    For packages, you can use
    :py:class:`latexpp.fixes.usepackage.CopyLocalPkgs`.  For figures, consider
    using :py:class:`latexpp.fixes.figures.CopyAndRenameFigs`.

    Arguments:
    
    - `files`: a list of files to include in the output directory.  The files
      are not renamed and subdirectories are preserved.

      Each element in `files` is either:
    
        - a single file name, in which case the destination file name and
          relative path is preserved, or

        - a dictionary of the form ``{'from': source_file, 'to': dest_file}``,
          in which case the file `source_file` is copied to `dest_file`, where
          `dest_file` is relative to the output directory.

    Example::
    
       fixes:
       [...]
       - name: 'latexpp.fixes.deps.CopyFiles'
         config:
           files:
             # copy my-suppl-mat-xyz.pdf -> output/SupplMaterial.pdf
             - from: my-suppl-mat-xyz.pdf
               to: SupplMaterial.pdf
             # copy ReplyReferees.pdf -> output/ReplyReferees.pdf
             - ReplyReferees.pdf
    """

    def __init__(self, files=[]):
        super().__init__()
        self.files = files

    def initialize(self, **kwargs):

        for fn in self.files:
            if isinstance(fn, dict):
                fn_from, fn_to = fn['from'], fn['to']
            else:
                fn_from, fn_to = fn, fn
            self.lpp.copy_file(fn_from, fn_to)

