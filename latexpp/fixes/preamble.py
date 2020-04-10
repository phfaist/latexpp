
from latexpp.fix import BaseFix


class AddPreamble(BaseFix):
    r"""
    Include arbitrary LaTeX code before ``\begin{document}``.

    Arguments:

      - `preamble`: the additional code to include before ``\begin{document}``.
    """
    def __init__(self, preamble=None, fromfile=None):
        super().__init__()
        self.preamble = preamble
        if fromfile:
            with open(fromfile) as f:
                if self.preamble and self.preamble[-1:] != "\n":
                    self.preamble += "\n"
                self.preamble += f.read()

    def add_preamble(self, **kwargs):
        return self.preamble
