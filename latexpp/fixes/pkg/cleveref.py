import re
import os
import os.path
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fix import BaseFix


class ResolveCleverefs(BaseFix):
    r"""
    Expands references to external links made via the `cleveref` package.

    The expansion of the reference commands are computed by running LaTeX on a
    specially-generated temporary document in a temporary directory.
    """
    def __init__(self, remove_usepackage=True, latex_command='pdflatex'):
        super().__init__()
        self.remove_usepackage = remove_usepackage
        self.stage = None
        self.collected_cmds = []
        self.resolved_cmds = {}
        self.latex_command = latex_command

        self.cref_macros = set( ('cref', 'Cref', 'cpageref', 'Cpageref',) ) # TODO: support more cmds

    def specs(self, **kwargs):
        return dict(macros=[
            MacroSpec('cref', args_parser=MacroStandardArgsParser('*{')),
            MacroSpec('Cref', args_parser=MacroStandardArgsParser('*{')),
            MacroSpec('cpageref', args_parser=MacroStandardArgsParser('*{')),
            MacroSpec('Cpageref', args_parser=MacroStandardArgsParser('*{')),
            # TODO: \crefrange, \Crefrange, \cpagerefrange, \Cpagerefrange,
            # \name[cC]ref, \labelcref, \labelcpageref
        ])

    def initialize(self):
        # read the aux file and keep it in memory--will be needed when we run latex.
        self.auxfile_contents = self._get_auxfile_contents()

    def _get_auxfile_contents(self):
        # separate function so it can be monkey-patched in tests
        auxfn = re.sub(r'(\.(la)?tex)$', '.aux', self.lpp.main_doc_fname)
        with open(auxfn) as f:
            return f.read()


    def preprocess(self, nodelist):
        # Normally, we shouldn't subclass preprocess() because the complicated
        # mechanics of descending into leaf nodes is already done for us in
        # BaseFix.  But here we need to access the global document structure to
        # create the auxiliary latex file and run it.  To actually descend into
        # the leaf nodes, we call the `super()` (BaseFix)'s `preprocess()`
        # implementation.
        #
        # What we do is that we perform a two-stage pass.  First (``self.stage
        # == "collect-refs"``) we simply collect all references.  Then we run
        # latex on a suitable auxiliary latex document that outputs the
        # expansions of the cref commands using the crossreftools package via
        # special TeX commands.  In a second stage (``self.stage ==
        # "replace-crefs"``) we expand the cref's into their respective
        # expansions.
        #

        #
        # preprocess() is called recursively for child nodes.  When we have set
        # a self.stage, let the super() class do everything.
        #
        if self.stage is not None:
            return super().preprocess(nodelist)


        self.stage = "collect-refs"

        #logger.debug("".join([n.to_latex() for n in nodelist]))

        # there is no reason newnodelist should differ from nodelist, BTW
        newnodelist = super().preprocess(nodelist)

        #logger.debug("".join([n.to_latex() for n in newnodelist]))

        logger.debug("collected_cmds = %r", self.collected_cmds)

        #
        # recompose the whole document preamble and get refs
        #
        try:
            i = next( (i for i, n in enumerate(nodelist)
                       if (n.isNodeType(latexwalker.LatexEnvironmentNode)
                           and n.environmentname == 'document')) )
        except StopIteration:
            raise ValueError("Couldn't find \\begin{document}")
        preamblelist = nodelist[:i]
        
        self._get_run_ltx_resolved_cmds("".join([n.to_latex() for n in preamblelist]))
        
        self.stage = "replace-crefs"

        return super().preprocess(newnodelist)


    def fix_node(self, n, **kwargs):
        if self.stage == "collect-refs":
            if n.isNodeType(latexwalker.LatexMacroNode):
                if n.macroname in self.cref_macros:
                    self.collected_cmds.append(n.to_latex())
        elif self.stage == "replace-crefs":
            if n.isNodeType(latexwalker.LatexMacroNode):
                # FIXME: check for \usepackage, too, and remove a \usepackage{cleveref} command 
                if n.macroname in self.cref_macros:
                    ltx = n.to_latex()
                    if ltx not in self.resolved_cmds:
                        raise RuntimeError("No resolved substitution for cleveref expression ‘{}’")
                    return self.resolved_cmds[ltx]
        else:
            raise RuntimeError("Invalid self.stage = {}".format(self.stage))

        return None # keep node as is & descend into children



    def _get_run_ltx_resolved_cmds(self, doc_preamble):
        """
        Given a full document preamble latex, resolve the given cleveref commands
        """

        with tempfile.TemporaryDirectory() as tmpdirname:
            logger.debug("Using temporary directory %s", tmpdirname)
            tmpltxfn = os.path.join(tmpdirname, 'tmp.tex')
            with open(tmpltxfn, 'w') as f:
                f.write(doc_preamble)
                f.write(r"""
\makeatletter
\@ifpackagelater{cleveref}{2018/03/27}
{
% OK, new version
}
{%
\PackageError{latexpp.fix.pkg.cleveref}{Your cleveref is too old, please upgrade to 2018/03/27+}{}%
}%
""")
                f.write(r"\makeatletter"+"\n")
                f.write(self.auxfile_contents)
                f.write(r"""
\begin{document}
\begingroup
  \makeatletter
\def\MakeUppercase{\noexpand\protect\noexpand\MakeUppercase}
\def\MakeLowercase{\noexpand\protect\noexpand\MakeLowercase}

\def\myextractcref#1#2{
  \def\tmp@save{}
  #2
  \message{*!*!*!*!LATEXPP:fixes.pkg.cleveref:#1:{\tmp@save}!*!*!*!*}
}
\def\add@to@tmp@save#1{%
  \def\protect{\noexpand}%
  \protected@edef\x{#1}%
  \xdef\tmp@save{\tmp@save\detokenize\expandafter{\x}}%
}
\def\@@@setcref#1#2{%
  \cref@getlabel{#2}{\@templabel}#1{\@templabel}{}{}%
  \add@to@tmp@save{#1{\@templabel}{}{}}%
}
\def\@@@setcrefrange#1#2#3{%
  \cref@getlabel{#2}{\@labela}%
  \cref@getlabel{#3}{\@labelb}%
  \add@to@tmp@save{#1{\@labela}{\@labelb}{}{}{}{}}%
}
\def\@setcref@pairgroupconjunction{\add@to@tmp@save\crefpairgroupconjunction}%
\def\@setcref@middlegroupconjunction{\add@to@tmp@save\crefmiddlegroupconjunction}%
\def\@setcref@lastgroupconjunction{\add@to@tmp@save\creflastgroupconjunction}%
\def\@@@setcpageref#1#2{%
  \cpageref@getlabel{#2}{\@temppage}%
  \add@to@tmp@save{#1{\@temppage}{}{}}%
}
\def\@@@setcpagerefrange#1#2#3{%
  \cpageref@getlabel{#2}{\@pagea}%
  \cpageref@getlabel{#3}{\@pageb}%
  \add@to@tmp@save{#1{\@pagea}{\@pageb}{}{}{}{}}%
}
""")
                for j, cmd in enumerate(self.collected_cmds):
                    logger.debug("using cmd = %s", cmd)
                    f.write(r"""\myextractcref{%d}{%s}"""%(j, cmd) + "\n")
                f.write(r"""\endgroup\end{document}""" + "\n")

            # don't forget to set the TEXINPUTS
            doc_path = os.path.dirname(self.lpp.main_doc_fname)
            if not doc_path:
                doc_path = os.path.realpath(os.getcwd())
            env = dict(os.environ)
            env["TEXINPUTS"] = ":".join([doc_path, tmpdirname]) + ":" + env.get("TEXINPUTS","")
            logger.debug("TEXINPUTS is = %r  [cwd=%r]", env['TEXINPUTS'], os.getcwd())
            #logger.debug("env = %r", env)

            # now run LaTeX
            try:
                res = subprocess.run([self.latex_command, 'tmp.tex'],
                                     input=b'H\n', env=env,
                                     cwd=tmpdirname, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.warning("Failed to run LaTeX to obtain cleveref substitutions.  Errors =\n%s%s",
                               e.stdout.decode('utf-8'), e.stderr.decode('utf-8'))
                raise

            out = res.stdout.decode('utf-8')
            lwout = self.lpp.make_latex_walker(out)

            rx_magic = re.compile(r'\*\!\*\!\*\!\*\!LATEXPP:fixes\.pkg\.cleveref:(?P<cmd_id>\d+):')

            resolved_cmds_for_index = {}

            pos = 0
            while True:
                m = rx_magic.search(out, pos)
                if m is None:
                    break
                pos = m.end()
                
                (node, p, l) = lwout.get_latex_expression(pos)
                pos = p+l

                assert node.isNodeType(latexwalker.LatexGroupNode)
                the_expansion = out[p+1:p+l-1].replace('\n','')

                resolved_cmds_for_index[int(m.group('cmd_id'))] = the_expansion
                
            self.resolved_cmds = {self.collected_cmds[i]: v
                                  for i, v in resolved_cmds_for_index.items()}
            logger.debug("resolved_cmds = %r", self.resolved_cmds)






# Use cleveref's "poor man" mode.  Simply parse the .sed file and apply all
# replacements after we're finished processing the document.


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



class ApplyPoorMan(BaseFix):
    r"""
    Applies the replacements provided by `cleveref`\ 's "poor man" mode.

    UPDATE: You should prefer ResolveCleverefs fix instead if it works.

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

        # now apply these replacements onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname)) as of:
            main_out = of.read()

        for rep in replacements:
            main_out = rep[0].sub(rep[1], main_out)

        # re-write replaced stuff onto the final file
        with open(os.path.join(lpp.output_dir, lpp.main_doc_output_fname), 'w') as of:
            of.write(main_out)
        

