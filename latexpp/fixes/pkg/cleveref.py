import re
import os.path
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec
from pylatexenc import latexwalker



# Use cleveref's "poor man" mode.  Simply parse the .sed file and apply all
# replacements after we're finished processing the document.


class ApplyPoorManFixes(object):
    def __init__(self):
        pass

    def fix_node(self, n, lpp):
        return None

    def finalize(self, lpp):
        # read the cleveref-generated .sed file
        sedfn = re.sub('(\.(la)?tex)$', '', lpp.main_doc_fname) + '.sed'
        if not os.path.exists(sedfn):
            logger.error("Cannot find file %s. Are you sure you provided the "
                         "[poorman] option to \usepackage[poorman]{cleveref} "
                         "and that you ran (pdf)latex?")
        lpp.check_autofile_up_to_date(sedfn)

        replacements = []
        with open(sedfn) as sedf:
            for sedline in sedf:
                sedline = sedline.strip()
                if sedline:
                    s, orig, alias, g = sedline.split('/')
                    replacements.append( (re.compile(orig), alias) )

        # now apply these replacements onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname)) as of:
            main_out = of.read()

        for rep in replacements:
            main_out = rep[0].sub(rep[1], main_out)

        # re-write replaced stuff onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname), 'w') as of:
            of.write(main_out)
        




# # cref's own \newlabel instructions are of the form
# # "\newlabel{eq:my-label@cref}{{[equation][1][2]2.1}{3}}"
# rx_newlabelcref = re.compile(r"""
# \\newlabel \{ (?P<labelname>[^\}@]+) @cref \}
# \{
#   \{
#     \[(?P<countername>[^\]]*)\]
#     \[(?P<countervalue>[^\]]*)\]
#     \[(?P<counterprefix>[^\]]*)\]
#     (?P<counterformatted>[^\}]*)
#   \}
#   \{
#     (?P<pageno>[^\}]*
#   \}
# \}
# """, flags=re.VERBOSE)


# class SimpleReplaceCleverRefsFixes(object):
    
#     def __init__(self, use_hyperlink=False):
#         self.use_hyperlink = use_hyperlink

#         # a very poor man's cleveref---everything is capitalized, no languages,
#         # no nothing beyond your bare-bones \cref/\Cref.  (Really sorry Toby for
#         # butchering your beautiful package.)
        
#         self.crefnames = {
#             'equation': ('Equation', 'Equations'),
#             'figure': ('Figure', 'Figures'),
#             'subfigure': ('Figure', 'Figures'),
#             'table': ('Table', 'Tables'),
#             'subtable': ('Table', 'Tables'),
#             'page': ('Page', 'Pages'),
#             'part': ('Part', 'Parts'),
#             'chapter': ('Chapter', 'Chapters'),
#             'section': ('Section', 'Sections'),
#             'subsection': ('Section', 'Sections'),
#             'subsubsection': ('Section', 'Sections'),
#             'appendix': ('Appendix', 'Appendices'),
#             'subappendix': ('Appendix', 'Appendices'),
#             'subsubappendix': ('Appendix', 'Appendices'),
#             'subsubsubappendix': ('Appendix', 'Appendices'),
#             'enumi': ('Item', 'Items'),
#             'enumii': ('Item', 'Items'),
#             'enumiii': ('Item', 'Items'),
#             'enumiv': ('Item', 'Items'),
#             'enumv': ('Item', 'Items'),
#             'footnote': ('Footnote', 'Footnotes'),
#             'theorem': ('Theorem', 'Theorems'),
#             'lemma': ('Lemma', 'Lemmas'),
#             'corollary': ('Corollary', 'Corollaries'),
#             'proposition': ('Proposition', 'Propositions'),
#             'definition': ('Definition', 'Definitions'),
#             'result': ('Result', 'Results'),
#             'example': ('Example', 'Examples'),
#             'remark': ('Remark', 'Remarks'),
#             'note': ('Note', 'Notes'),
#             'algorithm': ('Algorithm', 'Algorithms'),
#             'listing': ('Listing', 'Listings'),
#             'line': ('Line', 'Lines'),
#         }

#         self.crefinfo = {}

#     def specs(self):
#         return dict(macros= (
#             MacroSpec('cref', '*{'),
#             MacroSpec('Cref', '*{'),
#             MacroSpec('cpageref', '*{'),
#             MacroSpec('Cpageref', '*{'),
#         ) )

#     def initialize(self, lpp):
#         # read aux file
#         auxfn = re.sub('(\.(la)?tex)$', '', lpp.main_doc_fname) + '.aux'
#         lpp.check_autofile_up_to_date(auxfn)
#         # scan aux file for cref info in aux file.  They are of the form
#         # "\newlabel{eq:my-label@cref}{{[equation][1][2]2.1}{3}}"
#         with open(auxfn) as auxf:
#             auxd = auxf.read()
#         for m in rx_newlabelcref.finditer(auxd):
#             labelname = m.group('labelname')
#             countername = m.group('countername')
#             countervalue = m.group('countervalue')
#             logger.debug("Detected cref label %s -> %s %s",
#                          labelname, countername, countervalue)
#             self.crefinfo[labelname] = m.groupdict()
        

#     def fix_node(self, n, lpp):

#         if n.isNodeType(LatexMacroNode) and n.macroname in ('cref', 'Cref', 'cpageref', 'Cpageref'):

#             if not n.nodeargd or len(n.nodeargd.argnlist) != 2:
#                 logger.warning("Invalid use of %s macro: %s", n.macroname, n.latex_verbatim())
#                 return None

#             refmacro, is_cap = {
#                 'cref': (r'\ref', False),
#                 'Cref': (r'\ref', True),
#                 'cpageref': (r'\pageref', False),
#                 'Cpageref': (r'\pageref', True),
#             }.get(n.macroname)

#             is_starred = n.nodeargd.argnlist[0] is not None
#             labelname = lpp.latexpp_group_contents(n.nodeargd.argnlist[1])

#             lblinfo = self.crefinfo.get(labelname, None)
#             if lblinfo is None:
#                 logger.warning("Unknown cref reference: %s", n.latex_verbatim())
#                 return None

#             # By default if we don't know of this counter type, simply
#             # capitalize counter name
#             name = self.crefnames.get(lblinfo['countername'],
#                                       lblinfo['countername'].capitalize())

#             def get_repl_content(name, refmacro, labelname):
#                 return r'%(name)s~%(refmacro)s{%(labelname)s}'%dict(
#                     name=name, refmacro=refmacro, labelname=labelname
#                 )
            
#             if is_starred or not self.use_hyperlink:
#                 return get_repl_content(name, refmacro, labelname)
#             return '\hyperref['+labelname+']{' + get_repl_content(name, refmacro+'*', labelname) + '}'
                

