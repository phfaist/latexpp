import os
import os.path
import shutil
import re

import logging

from pylatexenc import latexwalker


logger = logging.getLogger(__name__)




# node.comment does not contain first '%' comment char
rx_lpp_pragma_n = re.compile(r'^%!lpp\s*(?P<instruction>.*?)\s*$', flags=re.DOTALL)



class LatexPreprocessor(object):
    def __init__(self, output_dir='_latexpp_output', main_doc_fname=None,
                 main_doc_output_fname=None):
        super().__init__()

        self.output_dir = os.path.realpath(os.path.abspath(output_dir))
        self.main_doc_fname = main_doc_fname
        self.main_doc_output_fname = main_doc_output_fname

        # version of output_dir for displaying purposes
        self.display_output_dir = output_dir.rstrip('/') + '/'

        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

        if len(os.listdir(self.output_dir)):
            # TODO: in the future, add prog option --clean-output-dir that
            # removes all before outputting...
            logger.warning("Output directory %s is not empty", self.display_output_dir)

        self.latex_context = latexwalker.get_default_latex_context_db()
        self.latex_context.add_context_category('latexpp-categories-marker-end', macros=[], prepend=True)

        self.fixes = []

    def install_fix(self, fix, prepend=False):
        if prepend:
            self.fixes.insert(fix, 0)
        else:
            self.fixes.append(fix)

        if hasattr(fix, 'specs'):
            self.latex_context.add_context_category(
                'latexpp-fix:'+fix.__class__.__module__+'.'+fix.__class__.__name__,
                insert_before='latexpp-categories-marker-end',
                **fix.specs(),
            )


    def execute_main(self):
        self.execute(self.main_doc_fname, self.main_doc_output_fname)


    def execute(self, fname, output_fname):

        with open(fname, 'r') as f:
            s = f.read()

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

            # while True:
            #     m = rx_lpp_pragma.match(s, posi)
            #     if m is None:
            #         break
            #     posi = m.end()+1 # skip newline
            #     instruction = m.group('instruction')
            #     if instruction == 'skip-file':
            #         logger.debug("LPP pragma skip-file encountered --- disabling lpp for this round")
            #         return s
            #     else:
            #         raise ValueError("Invalid %%!lpp pragma: {}".format(instruction))

            nodelist = nx
            latex = ''
            j = 0
            while j < len(nodelist):
                n = nodelist[j]
                # lpp pragma?
                lpp_instruction = self._get_lpp_pragma(n)
                if lpp_instruction is not None:
                    if re.match(r'^skip\s*\{$', lpp_instruction): # start skipping nodes
                        while j < len(nodelist):
                            if self._get_lpp_pragma(nodelist[j]) == '}':
                                j += 1
                                break
                            j += 1
                        else: # not break
                            raise ValueError("Can't find closing brace for '%%!lpp skip {'")
                    continue

                this_one = self.latexpp(n)
                #logger.debug("processing node %r --> %r", n, this_one)
                latex += this_one
                j += 1

            return latex

        return self.latexpp_node(nx)

    def _get_lpp_pragma(self, n):
        if n is not None and n.isNodeType(latexwalker.LatexCommentNode):
            m = rx_lpp_pragma_n.match(n.comment)
            if m:
                return m.group('instruction')
        return None

    def latexpp_group_contents(self, n):
        if n.isNodeType(latexwalker.LatexGroupNode):
            return self.latexpp(n.nodelist)
        return self.latexpp(n)

    def latexpp_node(self, n):

        # subclass this method to filter nodes

        if n is None:
            return ""

        #
        # Special treatment for \begin{document}.  See if we have any preamble
        # definitions to add, and add them right before.
        #
        if n.isNodeType(latexwalker.LatexEnvironmentNode) and \
           n.environmentname == 'document' and \
           not getattr(n, '_latexpp_document_env_node_processed', False):
           # find preamble required by all fixes
           preamble_lines = []
           for fix in self.fixes:
               if hasattr(fix, 'add_preamble'):
                   preamble_lines.append(fix.add_preamble())
           n._latexpp_document_env_node_processed = True
           if preamble_lines:
               preamble_text = "\n%%%\n" + "\n".join(preamble_lines)+"\n%%%\n"
           else:
               preamble_text = ""
           return preamble_text + self.latexpp(n)

        #
        # *** Apply fixes to this node ***
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
            return self.fmt_arglist(n.nodeargd.argspec, n.nodeargd.argnlist)

        if n.isNodeType(latexwalker.LatexMacroNode):
            if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return n.latex_verbatim()
            
            # process arguments recursively
            return '\\'+n.macroname+n.macro_post_space + add_args(n)
            
        if n.isNodeType(latexwalker.LatexEnvironmentNode):
            # get environment behavior definition.

            return (r'\begin{' + n.environmentname + '}' +
                    add_args(n) +
                    "".join( self.latexpp(n.nodelist) ) +
                    r'\end{' + n.environmentname + '}')

        if n.isNodeType(latexwalker.LatexSpecialsNode):
            if n.nodeargd is None or n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
                # no arguments or unknown argument structure
                return n.latex_verbatim()
            
            # process arguments recursively
            return n.specials_chars + add_args(n)

        if n.isNodeType(latexwalker.LatexMathNode):
            return n.delimiters[0] + "".join( self.latexpp(n.nodelist) ) + n.delimiters[1]


        return n.latex_verbatim()
        
    
    #
    # More utilities for fixes to call via lpp.<method>
    #

    def fmt_arglist(self, argspec, argnlist):
        s = ''
        for at, an in zip(argspec, argnlist):
            if at == '*':
                s += an.latex_verbatim() if an is not None else ''
            elif at in ('[', '{'):
                s += self.latexpp(an)
            else:
                logger.warning("Unknown macro argtype %r", at)
                s += an.latex_verbatim() if an is not None else ''
        return s


    def copy_file(self, source, destfname=None):
        #
        # Copy the file `source` to the latexpp output directory.  If
        # `destfname` is not None, rename the file to `destfname`.
        #
        if destfname is not None:
            dest = os.path.join(self.output_dir, destfname)
        else:
            dest = self.output_dir

        logger.info("Copying file %s -> %s", source,
                    os.path.join(self.display_output_dir, destfname if destfname else ''))
        shutil.copy2(source, dest)
