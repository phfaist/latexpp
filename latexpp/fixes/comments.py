
from pylatexenc.latexwalker import LatexCommentNode, LatexMacroNode

from latexpp.fixes import BaseFix


class RemoveComments(BaseFix):
    r"""
    Remove all LaTeX comments from the latex document.

    Arguments:

    - `leave_percent`: If `True` (the default), then a full LaTeX comment is
      replaced by an empty comment, i.e., a single percent sign and whatever
      whitespace followed the comment (the whitespace is anyways ignored by
      LaTeX).  If `False`, then the comment and following whitespace is removed
      entirely.

    .. warning::

       There is a situation where `leave_percent=False` can yield invalid LaTeX
       code, so avoid it, or at least be aware that it can happen.  For instance::

         some \LaTeX% a comment here
         code

       would be replaced by::

         some \LaTeXcode

       which is invalid.

       [TODO: FIX THIS. CHECK PREVIOUS NODE AND ADD A SINGLE SPACE IF NECESSARY]
    """
    def __init__(self, leave_percent=True):
        super().__init__()
        self.leave_percent = leave_percent

    def fix_node(self, n, prev_node=None, **kwargs):

        if n.isNodeType(LatexCommentNode):
            if self.leave_percent:
                # sys.stderr.write("Ignoring comment: '%s'\n"% node.comment)
                return "%"+n.comment_post_space
            else:
                if prev_node is not None and prev_node.isNodeType(LatexMacroNode):
                    if not prev_node.macro_post_space and \
                       (not prev_node.nodeargd or not prev_node.nodeargd.argnlist
                        or all((not a) for a in prev_node.nodeargd.argnlist)):
                        # macro has neither post-space nor any arguments, so add
                        # space to ensure LaTeX code stays valid
                        prev_node.macro_post_space = ' '
                    
                return [] # remove entirely.

        return None
