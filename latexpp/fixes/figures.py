import os
import os.path
import shutil

from pylatexenc.latexwalker import LatexMacroNode

from latexpp.fixes import BaseFix


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
        # By default we start at Fig #1 because journals like separate files
        # with numbered figures starting at 1
        self.fig_counter = start_fig_counter
        self.fig_rename = fig_rename

    def fix_node(self, n, lpp, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname == 'includegraphics':
            # note, argspec is '[{'

            # find file and copy it

            # arg is a group necessarily (unlikely to have single-char file name...)
            orig_fig_name = "".join(nn.latex_verbatim() for nn in n.nodeargd.argnlist[1].nodelist)
            ext = ''
            for e in exts:
                if os.path.exists(orig_fig_name+e):
                    orig_fig_name = orig_fig_name+e
                    ext = e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r", orig_fig_name, exts)
                return None # keep the node as it is
            
            if '.' in orig_fig_name:
                orig_fig_basename, orig_fig_ext = orig_fig_name.rsplit('.', maxsplit=1)
                orig_fig_ext = '.'+orig_fig_ext
            else:
                orig_fig_basename, orig_fig_ext = orig_fig_name, ''

            figoutname = self.fig_rename.format(
                fig_counter=self.fig_counter,
                fig_ext=orig_fig_ext,
                orig_fig_name=orig_fig_name,
                orig_fig_basename=orig_fig_basename,
                orig_fig_ext=orig_fig_ext
            )

            lpp.copy_file(picfname, figoutname)

            return r'\includegraphics' + \
                (n.nodeargd.argnlist[0].latex_verbatim() if n.nodeargd.argnlist[0] else '') + \
                '{' + figoutname + '}'

        return None

