
from latexpp.fixes import BaseFix


class AddPreamble(BaseFix):
    r"""
    Include arbitrary LaTeX code before ``\begin{document}``.

    Arguments:

      - `preamble`: the additional code to include before ``\begin{document}``.
    """
    def __init__(self, preamble):
        super().__init__()
        self.preamble = preamble

    def add_preamble(self, **kwargs):
        return self.preamble
