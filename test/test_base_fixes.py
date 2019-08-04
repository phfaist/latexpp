
import unittest

import helpers

from pylatexenc import latexwalker

from latexpp import fixes




class TestBaseFix(unittest.TestCase):

    def test_fix_nodelist(self):
        
        class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'testmacro':
                    return latexwalker.LatexMacroNode(macroname=r'replacemacro',
                                                      nodeargd=None,
                                                      pos=0,len=len(r'\replacemacro'))
                return None

        latex = r"""Test: \testmacro% a comment
Text and \`accent and \textbf{bold text} and $\vec b$ more stuff for Fran\c cois
\begin{enumerate}[(i)]
\item Hi there!  % here goes a comment
 \item[a] Hello!  @@@
     \end{enumerate}
Indeed thanks to \cite[Lemma 3]{Author}, we know that...
Also: {\itshape some italic text}."""

        nodelist = latexwalker.LatexWalker(latex, tolerant_parsing=False).get_latex_nodes()[0]

        myfix = MyFix()

        testnodelist = nodelist[0:1]+nodelist[2:4] # not \testmacro, all fix_node()'s return None
        newnodes = myfix.fix_nodelist(testnodelist)
        self.assertEqual(newnodes, testnodelist)

        testnodelist = nodelist[0:3] # with \testmacro
        newnodes = myfix.fix_nodelist(testnodelist)
        self.assertEqual(
            newnodes,
            testnodelist[0:1] + [
                latexwalker.LatexMacroNode(macroname=r'replacemacro',
                                           nodeargd=None,
                                           pos=0,len=len(r'\replacemacro'))
            ] + testnodelist[2:3]
        )


    def test_fix_nodelist(self):
        
        class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'testmacro':
                    return r'\newmacro {}'
                return None

        latex = r"""Test: \testmacro% a comment
Text and \`accent and \textbf{bold text} and $\vec b$ more stuff for Fran\c cois
\begin{enumerate}[(i)]
\item Hi there!  % here goes a comment
 \item[a] Hello!  @@@
     \end{enumerate}
Indeed thanks to \cite[Lemma 3]{Author}, we know that...
Also: {\itshape some italic text}."""

        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )

        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        newnodelist = myfix.fix_nodelist(nodelist[0:3])
        self.assertEqual( (newnodelist[0], newnodelist[3]), (nodelist[0], nodelist[2]) )
        self.assertEqual(
            (newnodelist[1].macroname, newnodelist[1].nodeargd.argnlist, newnodelist[1].macro_post_space,
             newnodelist[2].nodelist),
            (r'newmacro', [], ' ',
             [])
        )

    def test_preprocess_01(self):
        
        class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'testmacro':
                    return r'\newmacro {}'
                return None

        latex = r"""Test: \testmacro% a comment"""

        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )

        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 4)
        self.assertEqual( (newnodelist[0], newnodelist[3]), (nodelist[0], nodelist[2]) )
        self.assertEqual(
            (newnodelist[1].macroname, newnodelist[1].nodeargd.argnlist, newnodelist[1].macro_post_space,
             newnodelist[2].nodelist),
            (r'newmacro', [], ' ',
             [])
        )

    def test_preprocess_02(self):

        class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
                #print("fix_node: ", n)
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'testmacro':
                    #print("returning \\newmacro")
                    return r'\newmacro  {}'
                return None

        #
        # test that fix_node gets called for nodes in the following locations:
        #
        # - in environment argument(s) and environment body
        latex = r"""\begin{enumerate}[(\testmacro)]
\item hello \testmacro
\end{enumerate}"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 1)
        self.assertEqual(
            (newnodelist[0].nodeargd.argnlist[0].nodelist[1].macroname,
             newnodelist[0].nodeargd.argnlist[0].nodelist[1].macro_post_space,
             newnodelist[0].nodeargd.argnlist[0].nodelist[2].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[0].nodeargd.argnlist[0].nodelist[2].nodelist),
            (r"newmacro",
             '  ',
             True,
             [])
        )
        self.assertEqual(
            (newnodelist[0].nodelist[3].macroname,
             newnodelist[0].nodelist[3].macro_post_space,
             newnodelist[0].nodelist[4].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[0].nodelist[4].nodelist),
            (r'newmacro',
             '  ',
             True,
             [])
        )


        # - in macro argument(s)
        latex = r"""\chapter[Test \testmacro]{Yo \testmacro{} how do you do?}"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 1)
        self.assertEqual(
            (newnodelist[0].nodeargd.argnlist[1].nodelist[1].macroname,
             newnodelist[0].nodeargd.argnlist[1].nodelist[1].macro_post_space,
             newnodelist[0].nodeargd.argnlist[1].nodelist[2].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[0].nodeargd.argnlist[1].nodelist[2].nodelist,
             newnodelist[0].nodeargd.argnlist[2].nodelist[1].macroname,
             newnodelist[0].nodeargd.argnlist[2].nodelist[1].macro_post_space,
             newnodelist[0].nodeargd.argnlist[2].nodelist[2].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[0].nodeargd.argnlist[2].nodelist[2].nodelist),
            (r"newmacro",
             '  ',
             True,
             [],
             r"newmacro",
             '  ',
             True,
             [])
        )

        # - in math modes
        latex = r"""$\alpha + \testmacro$ and \[\testmacro - \beta\]"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 3)
        self.assertEqual(
            (newnodelist[0].nodelist[2].macroname,
             newnodelist[0].nodelist[2].macro_post_space,
             newnodelist[0].nodelist[3].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[0].nodelist[3].nodelist),
            (r"newmacro",
             '  ',
             True,
             [],)
        )
        self.assertEqual(
            (newnodelist[2].nodelist[0].macroname,
             newnodelist[2].nodelist[0].macro_post_space,
             newnodelist[2].nodelist[1].isNodeType(latexwalker.LatexGroupNode),
             newnodelist[2].nodelist[1].nodelist),
            (r"newmacro",
             '  ',
             True,
             [],)
        )




if __name__ == '__main__':
    helpers.test_main()
