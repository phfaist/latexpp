import os
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode
#from pylatexenc.latexencode import unicode_to_latex

from latexpp.fix import BaseFix


exts = ['', '.pdf', '.png', '.jpg', '.jpeg', '.eps']


class CopyAndRenameFigs(BaseFix):
    r"""
    Copy graphics files that are included by ``\includegraphics`` commands to
    the output directory.  By default, they are renamed in figure order,
    'fig-01.ext', 'fig-02.ext', etc.

    Arguments:

    - `fig_rename`: Template to use when renaming the graphics file in the
      output directory.  The string is parsed by python's ``str.format()``
      mechanism, and the following keys are provided:
    
        - '{fig_counter}', '{fig_counter:02}' -- the figure number.  Use ':0n'
          to format the number with `n` digits and leading zeros.

        - '{fig_ext}' -- the file name extension, including the dot.

        - '{orig_fig_name}' -- the original figure file name

        - '{orig_fig_basename}' -- the original figure file name, w/o extension

        - '{orig_fig_ext}' -- the original figure file extension

    - `start_fig_counter`: Figure numbering starts at this number (by default,
      1).
    """

    def __init__(self, fig_rename='fig-{fig_counter:02}{fig_ext}',
                 start_fig_counter=1):
        super().__init__()

        # By default we start at Fig #1 because journals like separate files
        # with numbered figures starting at 1
        self.fig_counter = start_fig_counter
        self.fig_rename = fig_rename

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname == 'includegraphics':
            # note, argspec is '[{'

            # find file and copy it
            orig_fig_name = self.preprocess_arg_latex(n, 1)
            for e in exts:
                if os_path.exists(orig_fig_name+e):
                    orig_fig_name = orig_fig_name+e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", orig_fig_name, exts)
                return None # keep the node as it is
            
            if '.' in orig_fig_name:
                orig_fig_basename, orig_fig_ext = orig_fig_name.rsplit('.', maxsplit=1)
                orig_fig_basename = os_path.basename(orig_fig_basename)
                orig_fig_ext = '.'+orig_fig_ext
            else:
                orig_fig_basename, orig_fig_ext = os_path.basename(orig_fig_name), ''

            figoutname = self.fig_rename.format(
                fig_counter=self.fig_counter,
                fig_ext=orig_fig_ext,
                orig_fig_name=orig_fig_name,
                orig_fig_basename=orig_fig_basename,
                orig_fig_ext=orig_fig_ext
            )

            # increment fig counter
            self.fig_counter += 1

            self.lpp.copy_file(orig_fig_name, figoutname)

            # don't use unicode_to_latex(figoutname) because actually we would
            # like to keep the underscores as is, \includegraphics handles it I
            # think
            return r'\includegraphics' + self.preprocess_latex(self.node_get_arg(n, 0)) + \
                '{' + figoutname + '}'
        

        return None

