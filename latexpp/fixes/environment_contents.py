import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexEnvironmentNode

from latexpp.fix import BaseFix


class InsertPrePost(BaseFix):
    r"""
    Find specific environment instances (e.g., \begin{proof} ... \end{proof})
    and insert given contents within the environment, before and/or after the
    inner environment body.
    """
    def __init__(self, environmentnames=None, pre_contents=None, post_contents=None):
        super().__init__()
        self.environmentnames = environmentnames if environmentnames else []
        self.pre_contents = pre_contents
        self.post_contents = post_contents

    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexEnvironmentNode) \
           and n.environmentname in self.environmentnames:

            # process the children nodes, including environment arguments etc.
            self.preprocess_child_nodes(n)

            # insert pre-/post- content to body
            if self.pre_contents is not None:
                # insert the pre- content
                pre_nodes = self.parse_nodes(self.pre_contents, n.parsing_state)
                n.nodelist[:0] = pre_nodes
            if self.post_contents is not None:
                # insert the post- content
                post_nodes = self.parse_nodes(self.post_contents, n.parsing_state)
                n.nodelist[len(n.nodelist):] = post_nodes

            return n

        return None
