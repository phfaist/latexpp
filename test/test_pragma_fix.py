
import unittest

import helpers

from pylatexenc import latexwalker

from latexpp.pragma_fix import PragmaFix

from .helpers import LatexWalkerNodesComparer

class TestPragmaFix(unittest.TestCase, LatexWalkerNodesComparer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_preprocess_00(self):
        
        class MyFix(PragmaFix):
            def fix_pragma_simple(self, nodelist, j, instruction, args):
                assert nodelist[j].isNodeType(latexwalker.LatexCommentNode)
                assert nodelist[j].comment.startswith('%!lpp ')
                if instruction == 'say-hello':
                    nodelist[j] = nodelist[j].parsing_state.lpp_latex_walker.make_node(
                        latexwalker.LatexCharsNode,
                        chars="Hello, World!"
                        parsing_state=nodelist[j].parsing_state,
                        pos=None, len=None
                    )
                    return j+1

                # continue processing
                return j+1

        latex = r"""
\documentclass{article}
\begin{document}
I have something to say:
%%!lpp say-hello

The same, but emphasized: \emph{%
%%!lpp say-hello
}.
\end{document}
""".lstrip()

        lw = latexwalker.LatexWalker(latex, tolerant_parsing=False)
        nodelist = lw.get_latex_nodes()[0]

        myfix = MyFix()

        newnodes = myfix.preprocess(nodelist)

        self.assert_nodelists_equal(
            newnodes,
            [
                {
                    "macro_post_space": "",
                    "colno": 0,
                    "lineno": 1,
                    "macroname": "documentclass",
                    "pos": 0,
                    "nodetype": "LatexMacroNode",
                    "len": 23,
                    "nodeargd": {
                        "argnlist": [
                            null,
                            {
                                "colno": 14,
                                "delimiters": [
                                    "{",
                                    "}"
                                ],
                                "nodelist": [
                                    {
                                        "colno": 15,
                                        "lineno": 1,
                                        "chars": "article",
                                        "nodetype": "LatexCharsNode",
                                        "pos": 15,
                                        "len": 7
                                    }
                                ],
                                "lineno": 1,
                                "pos": 14,
                                "nodetype": "LatexGroupNode",
                                "len": 9
                            }
                        ],
                        "argspec": "[{"
                    }
                },
                {
                    "colno": 23,
                    "lineno": 1,
                    "chars": "\n",
                    "nodetype": "LatexCharsNode",
                    "pos": 23,
                    "len": 1
                },
                {
                    "colno": 0,
                    "nodeargd": {
                        "argnlist": [],
                        "argspec": ""
                    },
                    "nodelist": [
                        {
                            "colno": 16,
                            "lineno": 2,
                            "chars": "\nI have something to say:\n",
                            "nodetype": "LatexCharsNode",
                            "pos": 40,
                            "len": 26
                        },
                        {
                            "colno": 0,
                            "lineno": 4,
                            "chars": "Hello, world!"
                            "nodetype": "LatexCharsNode",
                            "pos": 66,
                            "len": 16
                        },
                        {
                            "colno": 16,
                            "lineno": 4,
                            "chars": "\n\nThe same, but emphasized: ",
                            "nodetype": "LatexCharsNode",
                            "pos": 82,
                            "len": 28
                        },
                        {
                            "macro_post_space": "",
                            "colno": 26,
                            "lineno": 6,
                            "macroname": "emph",
                            "pos": 110,
                            "nodetype": "LatexMacroNode",
                            "len": 26,
                            "nodeargd": {
                                "argnlist": [
                                    {
                                        "colno": 31,
                                        "delimiters": [
                                            "{",
                                            "}"
                                        ],
                                        "nodelist": [
                                            {
                                                "colno": 32,
                                                "lineno": 6,
                                                "comment": "",
                                                "comment_post_space": "\n",
                                                "nodetype": "LatexCommentNode",
                                                "pos": 116,
                                                "len": 2
                                            },
                                            {
                                                "colno": 0,
                                                "lineno": 7,
                                                "comment": "%!lpp say-hello",
                                                "comment_post_space": "\n",
                                                "nodetype": "LatexCommentNode",
                                                "pos": 118,
                                                "len": 17
                                            }
                                        ],
                                        "lineno": 6,
                                        "pos": 115,
                                        "nodetype": "LatexGroupNode",
                                        "len": 21
                                    }
                                ],
                                "argspec": "{"
                            }
                        },
                        {
                            "colno": 1,
                            "lineno": 8,
                            "chars": ".\n",
                            "nodetype": "LatexCharsNode",
                            "pos": 136,
                            "len": 2
                        }
                    ],
                    "lineno": 2,
                    "pos": 24,
                    "nodetype": "LatexEnvironmentNode",
                    "len": 128,
                    "environmentname": "document"
                },
                {
                    "colno": 14,
                    "lineno": 9,
                    "chars": "\n\n",
                    "nodetype": "LatexCharsNode",
                    "pos": 152,
                    "len": 2
                }
            ]
        )


    def test_preprocess_00b(self):
        
        class MyFix(BaseFix):
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

        newnodelist = myfix.preprocess(nodelist[0:3])
        self.assertEqual( (newnodelist[0], newnodelist[3]), (nodelist[0], nodelist[2]) )
        self.assertEqual(
            (newnodelist[1].macroname, newnodelist[1].nodeargd.argnlist, newnodelist[1].macro_post_space,
             newnodelist[2].nodelist),
            (r'newmacro', [], ' ',
             [])
        )

    def test_preprocess_01(self):
        
        class MyFix(BaseFix):
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

        class MyFix(BaseFix):
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


    def test_preprocess_recursively(self):
        
        class MyFix(BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'textbf':
                    if n.nodeargd is None or not n.nodeargd.argnlist \
                       or not n.nodeargd.argnlist[0]:
                        return None
                    return r'\myboldtext {' \
                        + self.preprocess_contents_latex(n.nodeargd.argnlist[0]) + '}'
                if n.isNodeType(latexwalker.LatexEnvironmentNode) \
                   and n.environmentname == 'enumerate':
                    if n.nodeargd is None or not n.nodeargd.argnlist or not n.nodeargd.argnlist[0]:
                        return r'\mystuff{' + self.preprocess_contents_latex(n.nodelist) + '}'
                    return r'\mystuff[' + self.preprocess_arg_latex(n, 0) \
                        + ']{' + self.preprocess_latex(n.nodelist) + '}'
                return None

        latex = r"""
\begin{enumerate}[\textbf{recursive} replacement]text text\end{enumerate}"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        newlatex = lpp.nodelist_to_latex(newnodelist)
        self.assertEqual(
            newlatex,
            r"""
\mystuff[\myboldtext {recursive} replacement]{text text}"""
        )        
        

    def test_preprocess_recursively_2(self):
        
        class MyFix(BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'textbf':
                    if n.nodeargd is None or not n.nodeargd.argnlist \
                       or not n.nodeargd.argnlist[0]:
                        return None
                    return r'\myboldtext {' + self.preprocess_arg_latex(n, 0) + '}'
                if n.isNodeType(latexwalker.LatexEnvironmentNode) \
                   and n.environmentname == 'enumerate':
                    if n.nodeargd is None or not n.nodeargd.argnlist or not n.nodeargd.argnlist[0]:
                        return r'\mystuff{' + self.preprocess_latex(n.nodelist) + '}'
                    return r'\mystuff[' + self.preprocess_arg_latex(n, 0) \
                        + ']{' + self.preprocess_latex(n.nodelist) + '}'
                return None

        latex = r"""
\begin{enumerate}
\item Some \textbf{BOLD \textbf{text} AND MORE} and more.
\item And a sublist:
  \begin{enumerate}[\textbf{recursive} replacement]
  \item[\textbf{in \textbf{macro} optional argument}]
  \end{enumerate}
\item And in math mode $a\textbf{v} = \textbf{w+\textbf{z}+x}$
\end{enumerate}
"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        newlatex = lpp.nodelist_to_latex(newnodelist)
        self.assertEqual(
            newlatex,
            r"""
\mystuff{
\item Some \myboldtext {BOLD \myboldtext {text} AND MORE} and more.
\item And a sublist:
  \mystuff[\myboldtext {recursive} replacement]{
  \item[\myboldtext {in \myboldtext {macro} optional argument}]
  }
\item And in math mode $a\myboldtext {v} = \myboldtext {w+\myboldtext {z}+x}$
}
"""
        )

    def test_preprocess_recursively_3(self):
        
        class MyFix(BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode):
                    #print("Try fix ", n)
                    if n.macroname == 'ket':
                        if n.nodeargd is None or not n.nodeargd.argnlist \
                           or not n.nodeargd.argnlist[0]:
                            return None
                        return r'| {' + self.preprocess_arg_latex(n, 0) + r'} \rangle'
                    if n.macroname == r'rhostate':
                        return r'\hat\rho'
                return None

        latex = r"""\ket\rhostate"""
        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )
        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]
        newnodelist = myfix.preprocess(nodelist)
        newlatex = lpp.nodelist_to_latex(newnodelist)
        self.assertEqual(
            newlatex,
            r"""| {\hat\rho} \rangle"""
        )


    def test_preprocess_macrospace(self):

        class MyFix(BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'rho':
                    return r'\hat\sigma'
                return None

        latex = r"""The projected state $P_k\rho  P_{k'}$"""

        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )

        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 2)
        self.assertEqual( newnodelist[0], nodelist[0] )
        self.assertTrue( newnodelist[1].isNodeType(latexwalker.LatexMathNode) )
        self.assertEqual( len(newnodelist[1].nodelist), 4 )
        self.assertEqual( (newnodelist[1].nodelist[0], newnodelist[1].nodelist[2]),
                          (nodelist[1].nodelist[0], nodelist[1].nodelist[2]) )
        m1 = newnodelist[1].nodelist[1]
        self.assertEqual(
            (m1.macroname, m1.macro_post_space,
             m1.nodeargd.argnlist[0].macroname, m1.nodeargd.argnlist[0].macro_post_space),
            (r'hat', '', r'sigma', ' ')
        )
        

    def test_preprocess_macroarg(self):

        class MyFix(BaseFix):
            def fix_node(self, n, **kwargs):
                if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'hello':
                    return r'Hello !'
                return None

        latex = r"""\textbf\hello"""

        lpp = helpers.MockLPP()
        myfix = MyFix()
        lpp.install_fix( myfix )

        lw = lpp.make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        newnodelist = myfix.preprocess(nodelist)
        self.assertEqual(len(newnodelist), 1)
        self.assertTrue( newnodelist[0].isNodeType(latexwalker.LatexMacroNode) )
        m = newnodelist[0]
        self.assertEqual( len(m.nodeargd.argnlist), 1 )
        g = m.nodeargd.argnlist[0]
        self.assertTrue( g.isNodeType(latexwalker.LatexGroupNode) )
        self.assertEqual( len(g.nodelist), 1 )
        c = g.nodelist[0]
        self.assertTrue( c.isNodeType(latexwalker.LatexCharsNode) )
        self.assertEqual( c.chars, "Hello !" )
        


if __name__ == '__main__':
    helpers.test_main()
