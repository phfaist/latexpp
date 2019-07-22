
from pylatexenc.latexwalker import LatexCommentNode


class Fixes(object):

    def fix_node(self, n, lpp):

        if n.isNodeType(LatexCommentNode):
            # sys.stderr.write("Ignoring comment: '%s'\n"% node.comment)
            return "%"+n.comment_post_space

        return None
