import re
import os.path
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec
from pylatexenc import latexwalker


def bulk_replace(s, dic):
    rx = re.compile( "|".join( re.escape(k)
                               for k in sorted(dic.keys(), key=len, reverse=True) ) )
    return rx.sub(lambda m: dic[m.group()], s)

def sed_to_py_re(pat):
    # it's important to do the replacements in one go, and not
    # pat.replace(...).replace(...)....
    return bulk_replace(pat, {
        '\\(': '(',
        '\\)': ')',
        '\\{': '{',
        '\\}': '}',
        '{': '\\{',
        '}': '\\}',
    })


# Use cleveref's "poor man" mode.  Simply parse the .sed file and apply all
# replacements after we're finished processing the document.


class ApplyPoorManFixes(object):
    r"""
    Applies the replacements provided by `cleveref`\ 's "poor man" mode.

    Make sure you use `cleveref` with the ``[poorman]`` package option, like
    this::

        \usepackage[poorman]{cleveref}

    After this fix, the file no longer depends on the cleveref package.  Note,
    there are some limitations of cleveref's "poor man" mode that we can't get
    around here.
    """
    def __init__(self):
        pass

    def fix_node(self, n, lpp):
        return None

    def finalize(self, lpp):
        # read the cleveref-generated .sed file
        sedfn = re.sub('(\.(la)?tex)$', '', lpp.main_doc_fname) + '.sed'
        if not os.path.exists(sedfn):
            logger.error("Cannot find file %s. Are you sure you provided the "
                         "[poorman] option to \\usepackage[poorman]{cleveref} "
                         "and that you ran (pdf)latex?")
        lpp.check_autofile_up_to_date(sedfn)

        replacements = []
        with open(sedfn) as sedf:
            for sedline in sedf:
                sedline = sedline.strip()
                if sedline:
                    s, pat, repl, g = sedline.split('/')
                    pat = sed_to_py_re(pat)
                    replacements.append( (re.compile(pat), repl) )

        # now apply these replacements onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname)) as of:
            main_out = of.read()

        for rep in replacements:
            main_out = rep[0].sub(rep[1], main_out)

        # re-write replaced stuff onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname), 'w') as of:
            of.write(main_out)
        

