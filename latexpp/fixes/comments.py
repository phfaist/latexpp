
from pylatexenc.latexwalker import LatexCommentNode


class RemoveCommentsFixes(object):
    def __init__(self, leave_percent=True):
        self.leave_percent = leave_percent

    def fix_node(self, n, lpp):

        if n.isNodeType(LatexCommentNode):
            if self.leave_percent:
                # sys.stderr.write("Ignoring comment: '%s'\n"% node.comment)
                return "%"+n.comment_post_space
            else:
                return "" # remove entirely.

        return None
