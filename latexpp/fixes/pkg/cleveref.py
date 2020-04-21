import re
import os
import os.path
import logging

logger = logging.getLogger(__name__)

#from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser
#from pylatexenc import latexwalker

from latexpp.fix import BaseFix



class ApplyPoorMan(BaseFix):
    r"""
    Applies the replacements provided by `cleveref`\ 's "poor man" mode.

    .. warning::

       OBSOLETE: It is strongly recommended to use the
       :py:class:`latexpp.fixes.ref.ExpandRefs` fix instead, which supports
       `cleveref` references.

    Make sure you use `cleveref` with the ``[poorman]`` package option, like
    this::

        \usepackage[poorman]{cleveref}

    After this fix, the file no longer depends on the {cleveref} package.  Note,
    there are some limitations of cleveref's "poor man" mode that we can't get
    around here.
    """
    def __init__(self):
        super().__init__()

    def fix_node(self, n, **kwargs):
        return None

    def finalize(self, **kwargs):
        # read the cleveref-generated .sed file
        sedfn = re.sub(r'(\.(la)?tex)$', '', self.lpp.main_doc_fname) + '.sed'
        if not os.path.exists(sedfn):
            logger.error(r"Cannot find file %s. Are you sure you provided the "
                         r"[poorman] option to \usepackage[poorman]{cleveref} "
                         r"and that you ran (pdf)latex?")
        self.lpp.check_autofile_up_to_date(sedfn)

        replacements = []
        with open(sedfn) as sedf:
            for sedline in sedf:
                sedline = sedline.strip()
                if sedline:
                    s, pat, repl, g = sedline.split('/')
                    pat = sed_to_py_re(pat)
                    replacements.append( (re.compile(pat), repl) )

        lpp = self.lpp # ### NEEDED, RIGHT ??

        # now apply these replacements onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname)) as of:
            main_out = of.read()

        for rep in replacements:
            main_out = rep[0].sub(rep[1], main_out)

        # re-write replaced stuff onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname), 'w') as of:
            of.write(main_out)
        

