
import unittest

import helpers

from pylatexenc import latexwalker

from latexpp.pragma_fix import PragmaFix

from latexpp.fixes.builtin.skip import SkipPragma

from helpers import LatexWalkerNodesComparer, make_latex_walker

class TestPragmaFix(unittest.TestCase, LatexWalkerNodesComparer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_pragma_00(self):
        
        class MyFix(PragmaFix):
            def fix_pragma_simple(self, nodelist, j, instruction, args):
                assert nodelist[j].isNodeType(latexwalker.LatexCommentNode)
                assert nodelist[j].comment.startswith('%!lpp ')
                if instruction == 'say-hello':
                    nodelist[j] = nodelist[j].parsing_state.lpp_latex_walker.make_node(
                        latexwalker.LatexCharsNode,
                        chars="Hello, world!",
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

        lw = make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        myfix = MyFix()

        newnodes = myfix.preprocess(nodelist)

        self.assert_nodelists_equal(
            newnodes,
            [
                {
                    "nodetype": "LatexMacroNode",
                    "macroname": "documentclass",
                    "nodeargd": {
                        "argspec": "[{",
                        "argnlist": [
                            None,
                            {
                                "nodetype": "LatexGroupNode",
                                "nodelist": [
                                    {
                                        "nodetype": "LatexCharsNode",
                                        "chars": "article"
                                    }
                                ],
                                "delimiters": [
                                    "{",
                                    "}"
                                ]
                            }
                        ]
                    },
                    "macro_post_space": ""
                },
                {
                    "nodetype": "LatexCharsNode",
                    "chars": "\n"
                },
                {
                    "nodetype": "LatexEnvironmentNode",
                    "environmentname": "document",
                    "nodelist": [
                        {
                            "nodetype": "LatexCharsNode",
                            "chars": "\nI have something to say:\n"
                        },
                        {
                            "nodetype": "LatexCharsNode",
                            "chars": "Hello, world!"
                        },
                        {
                            "nodetype": "LatexCharsNode",
                            "chars": "\n\nThe same, but emphasized: "
                        },
                        {
                            "nodetype": "LatexMacroNode",
                            "macroname": "emph",
                            "nodeargd": {
                                "argspec": "{",
                                "argnlist": [
                                    {
                                        "nodetype": "LatexGroupNode",
                                        "nodelist": [
                                            {
                                                "nodetype": "LatexCommentNode",
                                                "comment": "",
                                                "comment_post_space": "\n"
                                            },
                                            {
                                                "nodetype": "LatexCharsNode",
                                                "chars": "Hello, world!"
                                            }
                                        ],
                                        "delimiters": [
                                            "{",
                                            "}"
                                        ]
                                    }
                                ]
                            },
                            "macro_post_space": ""
                        },
                        {
                            "nodetype": "LatexCharsNode",
                            "chars": ".\n"
                        }
                    ],
                    "nodeargd": {
                        "argspec": "",
                        "argnlist": []
                    }
                },
                {
                    "nodetype": "LatexCharsNode",
                    "chars": "\n"
                }
            ]
        )


    def test_pragma_01(self):
        
        class MyFix(PragmaFix):
            def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):
                assert nodelist[jstart].isNodeType(latexwalker.LatexCommentNode)
                assert nodelist[jstart].comment.startswith('%!lpp ')
                assert nodelist[jend-1].isNodeType(latexwalker.LatexCommentNode)
                assert nodelist[jend-1].comment.startswith('%!lpp ')
                if instruction == 'count-occurence':
                    # use arg
                    assert len(args) == 1
                    s = args[0]
                    scope_to_latex = "".join(n.to_latex() for n in nodelist[jstart+1:jend-1])
                    result = scope_to_latex.count(s) # number of substring occurrences

                    # - insert occurence report
                    ps = nodelist[jend-1].parsing_state
                    nodelist.insert(jend-1, ps.lpp_latex_walker.make_node(
                        latexwalker.LatexCharsNode,
                        chars="[Marked scope contains {} occurrences of the substring `{}']"
                        .format(result, s),
                        parsing_state=ps,
                        pos=None, len=None
                    ))

                    # remove LPP pragma instructions. CAREFUL: Indices must
                    # account for nodes that we have just inserted/deleted
                    del nodelist[jend]
                    del nodelist[jstart]
                    return jend-1 # one past end after accounting for deleted nodes
                
                # ignore pragma scope & continue processing
                return jend

        latex = r"""
\documentclass{article}
\begin{document}

%%!lpp count-occurence "lor" {

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. \emph{Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia deserunt mollit anim id est laborum.}

%%!lpp }

\end{document}
""".lstrip()

        lw = make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        myfix = MyFix()

        newnodes = myfix.preprocess(nodelist)

        self.assert_nodelists_equal(
            newnodes,
            [
                {
                    'nodetype': 'LatexMacroNode',
                    'macroname': 'documentclass',
                    'nodeargd': {
                        'argspec': '[{', 'argnlist': [
                            None, {'nodetype': 'LatexGroupNode',
                                   'nodelist': [{'nodetype': 'LatexCharsNode',
                                                 'chars': 'article'}],
                                   'delimiters': ['{', '}']}
                        ]
                    },
                    'macro_post_space': ''},
                {'nodetype': 'LatexCharsNode', 'chars': '\n'},
                {
                    'nodetype': 'LatexEnvironmentNode',
                    'environmentname': 'document',
                    'nodelist': [
                        {'nodetype': 'LatexCharsNode', 'chars': '\n\n'},
                        {'nodetype': 'LatexCharsNode',
                         'chars': '\n\nLorem ipsum dolor sit amet, consectetur '
                         'adipiscing elit, sed do eiusmod tempor\nincididunt ut labore '
                         'et dolore magna aliqua. Ut enim ad minim veniam, quis\n'
                         'nostrud exercitation ullamco laboris nisi ut aliquip ex '
                         'ea commodo\nconsequat. '},
                        {'nodetype': 'LatexMacroNode',
                         'macroname': 'emph',
                         'nodeargd': {'argspec': '{', 'argnlist': [
                             {'nodetype': 'LatexGroupNode', 'nodelist': [
                                 {'nodetype': 'LatexCharsNode',
                                  'chars': 'Duis aute irure dolor in reprehenderit '
                                  'in voluptate velit esse\ncillum dolore eu fugiat '
                                  'nulla pariatur. Excepteur sint occaecat cupidatat non\n'
                                  'proident, sunt in culpa qui officia deserunt mollit '
                                  'anim id est laborum.'}
                             ], 'delimiters': ['{', '}']}
                         ]},
                         'macro_post_space': ''},
                        {'nodetype': 'LatexCharsNode', 'chars': '\n\n'},
                        {'nodetype': 'LatexCharsNode',
                         'chars': "[Marked scope contains 4 occurrences of the substring `lor']"},
                        {'nodetype': 'LatexCharsNode', 'chars': '\n\n'}
                    ],
                    'nodeargd': {'argspec': '', 'argnlist': []}
                },
                {'nodetype': 'LatexCharsNode', 'chars': '\n'}
            ]
        )


    def test_pragma_skip(self):
        
        latex = r"""
\documentclass{article}
\begin{document}

%%!lpp skip {

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. \emph{Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia deserunt mollit anim id est laborum.}

%%!lpp }

But don't skip this.

\end{document}
""".lstrip()

        lw = make_latex_walker(latex)
        nodelist = lw.get_latex_nodes()[0]

        myfix = SkipPragma()

        newnodes = myfix.preprocess(nodelist)

        self.assert_nodelists_equal(
            newnodes,
            [
                {
                    'nodetype': 'LatexMacroNode',
                    'macroname': 'documentclass',
                    'nodeargd': {
                        'argspec': '[{', 'argnlist': [
                            None, {'nodetype': 'LatexGroupNode',
                                   'nodelist': [{'nodetype': 'LatexCharsNode',
                                                 'chars': 'article'}],
                                   'delimiters': ['{', '}']}
                        ]
                    },
                    'macro_post_space': ''},
                {'nodetype': 'LatexCharsNode', 'chars': '\n'},
                {
                    'nodetype': 'LatexEnvironmentNode',
                    'environmentname': 'document',
                    'nodelist': [
                        {'nodetype': 'LatexCharsNode', 'chars': '\n\n'},
                        {'nodetype': 'LatexCharsNode',
                         'chars': '\n\nBut don\'t skip this.\n\n'},
                    ],
                    'nodeargd': {'argspec': '', 'argnlist': []}
                },
                {'nodetype': 'LatexCharsNode', 'chars': '\n'}
            ]
        )




if __name__ == '__main__':
    helpers.test_main()
