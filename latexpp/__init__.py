import os
import os.path

import logging

from pylatexenc import latexwalker


logger = logging.getLogger(__name__)



class LatexPreprocessor(object):
    def __init__(self, output_dir='_latexpp_output'):
        super().__init__()

        self.output_dir = os.path.realpath(os.path.abspath(output_dir))

        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

        if len(os.listdir(self.output_dir)):
            # TODO: in the future, add prog option --clean-output-dir that
            # removes all before outputting...
            logger.warning("Output directory %s is not empty", self.output_dir)
        

        self.latex_context = latexwalker.get_default_latex_context_db()

        self.fixes = []

    def install_fix(self, fix, prepend=False):
        if prepend:
            self.fixes.insert(fix, 0)
        else:
            self.fixes.append(fix)

        if hasattr(fix, 'specs'):
            self.latex_context.add_context_category('latexpp-fix:'+fix.__class__.__name__,
                                                    **fix.specs())


    def execute(self, fname, output_fname):

        with open(fname, 'r') as f:
            s = f.read()

        # find \begin{document} ... \end{document}
        # assert no content after \end{document}
        # call latexwalker with pos=(position of \begin{document})

        # ### NOTE: also filter comments in preamble

        #pos_begin_document = s.find(r'\begin{document}')
        #if pos_begin_document == -1:
        #    raise ValueError(r"Can't find \begin{document}!")
        #
        #return s[:pos_begin_document] + self.execute_string(s)

        outdata = self.execute_string(s)

        with open(os.path.join(self.output_dir, output_fname), 'w') as f:
            f.write(outdata)


    def execute_string(self, s, pos=0):

        lw = latexwalker.LatexWalker(s, latex_context=self.latex_context,
                                     tolerant_parsing=False)
        
        #lw.debug_nodes = True
        
        (nodelist, pos, len_) = lw.get_latex_nodes(pos=pos)

        return self.latexpp(nodelist)


    def latexpp(self, nx):
        # subclass this method to filter nodes

        if isinstance(nx, list):
            nodelist = nx
            latex = ''
            for nn in nodelist:
                this_one = self.latexpp(nn)
                #logger.debug("processing node %r --> %r", nn, this_one)
                latex += this_one

            return latex

        return self.latexpp_node(nx)

    def latexpp_group_contents(self, n):
        if n.isNodeType(latexwalker.LatexGroupNode):
            return self.latexpp(n.nodelist)
        return self.latexpp(n)

    def latexpp_node(self, n):

        # subclass this method to filter nodes

        if n is None:
            return ""

        #
        # Apply fixes to this node
        #
        for fix in self.fixes:
            s = fix.fix_node(n, lpp=self)
            if s is not None:
                return s

        #
        # And then we recurse in the relevant node children
        #

        #if n.isNodeType(latexwalker.LatexCharsNode):  --- no children
        
        #if n.isNodeType(latexwalker.LatexCommentNode):  --- no children
        
        if n.isNodeType(latexwalker.LatexGroupNode):
            return n.delimiters[0] + "".join(self.latexpp(n.nodelist)) \
                + n.delimiters[1]
        
        def add_args(n):
            #logger.debug("add_args(%r)", n)
            if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return ''
            s = ''
            for at, an in zip(n.nodeargd.argspec, n.nodeargd.argnlist):
                if at == '*':
                    s += an.latex_verbatim() if an is not None else ''
                elif at in ('[', '{'):
                    s += self.latexpp(an)
                else:
                    logger.warning("Unknown macro argtype %r", at)
                    s += an.latex_verbatim() if an is not None else ''
            #logger.debug("---> %r", s)
            return s

        if n.isNodeType(latexwalker.LatexMacroNode):
            if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return n.latex_verbatim()
            
            # process arguments recursively
            return '\\'+n.macroname+n.macro_post_space + add_args(n)
            
        if n.isNodeType(latexwalker.LatexEnvironmentNode):
            # get environment behavior definition.

            return ('\\begin{' + n.environmentname + '}' +
                    add_args(n) +
                    "".join( self.latexpp(n.nodelist) ) +
                    '\\end{' + n.environmentname + '}')

        if n.isNodeType(latexwalker.LatexSpecialsNode):
            if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return n.latex_verbatim()
            
            # process arguments recursively
            return n.specials_chars + add_args(n)

        if n.isNodeType(latexwalker.LatexMathNode):
            return n.delimiters[0] + "".join( self.latexpp(n.nodelist) ) + n.delimiters[1]


        return n.latex_verbatim()
        
