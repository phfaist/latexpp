import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexEnvironmentNode

from latexpp.fix import BaseFix


class InsertPrePost(BaseFix):
    r"""
    Find instances of a specific environment and insert contents in its body,
    before or after the existing contents.

    This fix can be useful for instance to add a ``\qed`` command in some LaTeX
    styles at the end of proofs (``\begin{proof} ... \end{proof}`` →
    ``\begin{proof} ... \qed\end{proof}``).

    Arguments:

      - `environmentnames` is a list of names of environments upon which to act
        (e.g., ``['proof']``;

      - `pre_contents` is arbitrary LaTeX code to insert at the beginning of the
        environment body, for each environment encountered whose name is in
        `environmentnames`;

      - `post_contents` is arbitrary LaTeX code to insert at the end of the
        environment body, for each environment encountered whose name is in
        `environmentnames`.
    """
    def __init__(self, environmentnames=None, pre_contents=None, post_contents=None):
        super().__init__()
        self.environmentnames = list(environmentnames) if environmentnames else []
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
