import os.path

from pylatexenc import latexwalker


class LatexDocumentPreprocessor(object):
    def __init__(self, fname, output_dir, latexwalker_kwargs):
        super().__init__()
        self.fname = fname
        self.output_dir = output_dir
        self.latexwalker_kwargs = latexwalker_kwargs

    def execute(self):
        with open(self.fname, 'r') as f:
            s = f.read()

        # find \begin{document} ... \end{document}
        # assert no content after \end{document}
        # call latexwalker with pos=(position of \begin{document})

        pos_begin_document = s.find(r'\begin{document}')
        if pos_begin_document == -1:
            raise ValueError(r"Can't find \begin{document}!")
        
        return self.execute_string(s, pos_begin_document)


    def execute_string(self, s, pos):

        lw = latexwalker.LatexWalker(s, pos=pos, **self.latexwalker_kwargs)
        
        (nodelist, pos, len_) = lw.get_latex_nodes()

        latex = ''
        for n in nodelist:
            latex += self.latexpp(n)
            
        print("Preprocessed latex = ")
        print(latex)

        return latex


    def latexpp(self, n):
        # subclass this method
        return n.latex_verbatim()
        
