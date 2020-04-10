import re
import os
import os.path
import logging
import tempfile
import itertools
import subprocess

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fix import BaseFix

from .usepackage import node_get_usepackage # for detecting \usepackage{cleveref}

_REFCMDS =  {
    'ref': {
        'ref': {'macro': MacroSpec('ref', args_parser=MacroStandardArgsParser('*{')),
                'label_args': [1]},
        'pageref': {'macro': MacroSpec('pageref', args_parser=MacroStandardArgsParser('*{')),
                    'label_args': [1]},
    },
    'ams-eqref': {
        'eqref': {'macro': MacroSpec('eqref', args_parser=MacroStandardArgsParser('*{')),
                  'label_args': [1]},
    },
    'cleveref': {
        'cref': {'macro': MacroSpec('cref', args_parser=MacroStandardArgsParser('*{')),
                 'label_args': [1]},
        'Cref': {'macro': MacroSpec('Cref', args_parser=MacroStandardArgsParser('*{')),
                 'label_args': [1]},
        'cpageref': {'macro': MacroSpec('cpageref', args_parser=MacroStandardArgsParser('*{')),
                     'label_args': [1]},
        'Cpageref': {'macro': MacroSpec('Cpageref', args_parser=MacroStandardArgsParser('*{')),
                     'label_args': [1]},
        'crefrange': {'macro': MacroSpec('crefrange', args_parser=MacroStandardArgsParser('*{{')),
                      'label_args': [1,2]},
        'Crefrange': {'macro': MacroSpec('Crefrange', args_parser=MacroStandardArgsParser('*{{')),
                      'label_args': [1,2]},
        'cpagerefrange': {'macro': MacroSpec('cpagerefrange', args_parser=MacroStandardArgsParser('*{{')),
                          'label_args': [1,2]},
        'Cpagerefrange': {'macro': MacroSpec('Cpagerefrange', args_parser=MacroStandardArgsParser('*{{')),
                          'label_args': [1,2]},
        'namecref': {'macro': MacroSpec('namecref', args_parser=MacroStandardArgsParser('*{')),
                     'label_args': [1]},
        'nameCref': {'macro': MacroSpec('nameCref', args_parser=MacroStandardArgsParser('*{')),
                     'label_args': [1]},
        'lcnamecref': {'macro': MacroSpec('lcnamecref', args_parser=MacroStandardArgsParser('*{')),
                       'label_args': [1]},
        'namecrefs': {'macro': MacroSpec('namecrefs', args_parser=MacroStandardArgsParser('*{')),
                      'label_args': [1]},
        'nameCrefs': {'macro': MacroSpec('nameCrefs', args_parser=MacroStandardArgsParser('*{')),
                      'label_args': [1]},
        'lcnamecrefs': {'macro': MacroSpec('lcnamecrefs', args_parser=MacroStandardArgsParser('*{')),
                        'label_args': [1]},
    }
}



class ExpandRefs(BaseFix):
    r"""
    Expands references in the document.  Includes support for `cleveref`
    references.

    The expansion of the reference commands are computed by running LaTeX on a
    specially-generated temporary document in a temporary directory.

    Arguments:

    - `only_ref_types`: limit expansion to selected reference kind.  If
      non-`None`, it should be a set or list containing one or more of `('ref',
      'ams-eqref', 'cleveref')`

    - `make_hyperlinks`: If the `hyperref` package is loaded, then hyperlinks
      commands to the appropriate targets are generated in the document.

    - `expand_only_prefixes=['LIST', 'OF', 'PREFIXES']`: Only do the expansion
      for reference labels that start with one of the given prefixes.  This is
      useful, for instance, if you load labels from external documents with a
      prefix and you only want to expand those.

      One way to load external labels is with the `zref-xr` package::

          \usepackage{zref-xr}
          \zxrsetup{toltxlabel}
          \zexternaldocument*[PREFIX]{OtherDocument}

    - `remove_usepackage_cleveref`: remove any occurrence of
      ``\usepackage[options..]{cleveref}``.  Default: True if 'cleveref' is one
      of the reference types acted upon (see `only_ref_types`) and if the
      expansion is not for specific prefixes, otherwise False.
  
    - `latex_command`: latex executable to run.  By default, 'pdflatex'.  (Can
      also specify absolute path.)

    - `debug_latex_output`: If set to True, will print out LaTeX output in
      verbose mode (logger debug level).  Default: False
    """
    def __init__(self, *,
                 only_ref_types=None,
                 make_hyperlinks=True,
                 expand_only_prefixes=False,
                 remove_usepackage_cleveref=None,
                 latex_command='pdflatex',
                 debug_latex_output=False):

        super().__init__()

        if isinstance(only_ref_types, str):
            # single ref type
            self.ref_types = [ only_ref_types ]
        elif only_ref_types:
            # use sepecified ref types
            self.ref_types = list(only_ref_types)
        else:
            # by default, use all ref types
            self.ref_types = list(_REFCMDS.keys())

        self.make_hyperlinks = make_hyperlinks

        self.expand_only_prefixes = expand_only_prefixes

        if remove_usepackage_cleveref is not None:
            self.remove_usepackage_cleveref = remove_usepackage_cleveref
        else:
            self.remove_usepackage_cleveref = \
                ('cleveref' in self.ref_types and not  self.expand_only_prefixes)

        self.debug_latex_output = debug_latex_output

        self.stage = None
        self.collected_cmds = {k: [] for k in self.ref_types}
        self.resolved_cmds = {}
        self.latex_command = latex_command

        self.cmd_macros = {reftype: {k: d['macro'] for k,d in _REFCMDS[reftype].items()}
                           for reftype in self.ref_types}

    def specs(self, **kwargs):
        all_macros = itertools.chain(
            # for some reason, *[...] is required here...
            *[self.cmd_macros[reftype].values() for reftype in self.ref_types]
        )
        #all_macros = list(all_macros); logger.debug("Macros = %r", all_macros)
        return dict(macros=all_macros)

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

        doc_preamble = self._get_doc_preamble(nodelist)
        self._get_run_ltx_resolved_cmds(doc_preamble)
        
        self.stage = "replace-crefs"

        return super().preprocess(newnodelist)

    def _get_doc_preamble(self, doc_nodelist):
        #
        # Use original, unmodifed doc preamble.  So we have sections removed by
        # %%!lpp skip pragmas, etc. -- it's just safer
        #
        with open(self.lpp.main_doc_fname) as f:
            full_raw_doc_contents = f.read()

        # Minor caveat -- \begin{document} must be in the main latex file (but
        # we can probably ignore the rare edge cases).
        m = re.search(r'\\begin\s*\{document\}', full_raw_doc_contents)
        if m is None:
            raise ValueError("Couldn't find \\begin{document} in main file %s"%(self.lpp.main_doc_fname))
        
        return full_raw_doc_contents[:m.start()]

    def _get_doc_preamble_recomposed(self, doc_nodelist):
        # this method should not be used at all, except in the tests with a Mock
        # LPP

        #
        # recompose the whole document preamble and get refs
        #
        try:
            i = next( (i for i, n in enumerate(doc_nodelist)
                       if (n.isNodeType(latexwalker.LatexEnvironmentNode)
                           and n.environmentname == 'document')) )
        except StopIteration:
            raise ValueError("Couldn't find \\begin{document}")
        preamblelist = doc_nodelist[:i]
        return "".join([n.to_latex() for n in preamblelist])


    def fix_node(self, n, **kwargs):
        if self.stage == "collect-refs":

            if n.isNodeType(latexwalker.LatexMacroNode):
                for reftype in self.ref_types:
                    if n.macroname in self.cmd_macros[reftype]:
                        if self._check_prefix(reftype, n):
                            self.collected_cmds[reftype].append(n.to_latex())

        elif self.stage == "replace-crefs":

            if n.isNodeType(latexwalker.LatexMacroNode):
                if self.remove_usepackage_cleveref:
                    if node_get_usepackage(n, self) == 'cleveref':
                        return [] # remove this macro invocation

                for reftype in self.ref_types:
                    if n.macroname in self.cmd_macros[reftype]:
                        ltx = n.to_latex()
                        if ltx not in self.resolved_cmds[reftype]:
                            # probably not the requested prefix
                            return None
                        return self.resolved_cmds[reftype][ltx]

        else:
            raise RuntimeError("Invalid self.stage = {}".format(self.stage))

        return None # keep node as is & descend into children


    def _check_prefix(self, reftype, n):
        if n.nodeargd is None or n.nodeargd.argnlist is None:
            return False
        if not self.expand_only_prefixes:
            return True
        one_ok = False
        one_not_ok = False
        labels = list(itertools.chain( *[
            self.preprocess_contents_latex(n.nodeargd.argnlist[i]).split(',')
            for i in _REFCMDS[reftype][n.macroname]['label_args']
        ] ))
        logger.debug("cmd = %s, labels = %s", n.to_latex(), labels)
        for lbl in labels:
            if lbl.startswith(tuple(self.expand_only_prefixes)):
                one_ok = True
            else:
                one_not_ok = True
        if one_ok and one_not_ok:
            logger.warning("Reference ‘%s’ has one label with the requested prefix, and "
                           "one label without.  I cannot expand it!" %(n.to_latex()))
        if one_not_ok:
            return False
        return True

    def _get_run_ltx_resolved_cmds(self, doc_preamble):
        """
        Given a full document preamble latex, resolve the given cleveref commands
        """

        do_ref = ('ref' in self.ref_types and self.collected_cmds['ref'])
        do_amseqref = ('ams-eqref' in self.ref_types and self.collected_cmds['ams-eqref'])
        do_cleveref = ('cleveref' in self.ref_types and self.collected_cmds['cleveref'])

        with tempfile.TemporaryDirectory() as tmpdirname:
            logger.debug("Using temporary directory %s", tmpdirname)
            tmpltxfn = os.path.join(tmpdirname, 'tmp.tex')
            with open(tmpltxfn, 'w') as f:
                f.write(doc_preamble)
                f.write(r"""\makeatletter""" + "\n")
                if do_cleveref:
                    f.write(r"""
\@ifpackagelater{cleveref}{2018/03/27}
{
  % OK, new version
}
{%
  \PackageError{latexpp.fixes.ref}{latexpp refs expansion only works with cleveref at least 2018/03/27+, please upgrade.  You can obtain a newer cleveref.sty from CTAN.org and place it in the same folder as your LaTeX document}{}%
}%
""")
                f.write(r"""
\newif\ifLatexppRefUseHyperref
\@ifpackageloaded{hyperref}{\LatexppRefUseHyperreftrue}{\LatexppRefUseHyperreffalse}
""")
                if do_ref or do_amseqref:
                    # need to use crossreftools
                    f.write(r"""
\IfFileExists{crossreftools.sty}{\RequirePackage{crossreftools}}{
  \PackageError{latexpp.fixes.ref}{latexpp refs expansion with hyperref requires the package crossreftools.  You can obtain crossreftools.sty from CTAN.org and place it in the same folder as your LaTeX document}{}
}
""")

                #f.write(r"\makeatletter"+"\n") # already done above
                f.write(self.auxfile_contents)
                f.write(r"""
\begin{document}
""")

                # DO TRADITIONAL REFERENCES and AMS-EQREF REFERENCES
                if do_ref or do_amseqref:
                    f.write(r"""
\begingroup
\makeatletter
\def\hbox#1{#1}
\def\vbox#1{#1}
\def\@myref#1{\protected@edef\tmp@save{\crtextractref{reference}{#1}}}
\def\@mypageref#1{\protected@edef\tmp@save{\crtextractref{page}{#1}}}
""")
                    no_hyperlinks_code = r"""
\def\ref{\@ifstar\@myref\@myref}
\def\pageref{\@ifstar\@mypageref\@mypageref}
"""
                    if self.make_hyperlinks:
                        f.write(r"""
\ifLatexppRefUseHyperref
  \def\@mylinkref#1{\protected@edef\tmp@save{\protect\hyperref[#1]{\crtextractref{reference}{#1}}}}
  \def\@mylinkpageref#1{\protected@edef\tmp@save{\protect\hyperref[#1]{\crtextractref{page}{#1}}}}
  \def\ref{\@ifstar\@myref\@mylinkref}
  \def\pageref{\@ifstar\@mypageref\@mylinkpageref}
\else """ + no_hyperlinks_code + r"""\fi""" + "\n")
                    else:
                        f.write(no_hyperlinks_code)

                    f.write(r"""
\def\myextractref#1#2{
  #2
  \message{^^J*!*!*!*!LATEXPP:fixes.ref:ref:#1:{\detokenize\expandafter{\tmp@save}}!*!*!*!*}
}
""")
                    if do_ref:
                        for j, cmd in enumerate(self.collected_cmds['ref']):
                            logger.debug("using cmd = %s", cmd)
                            f.write(r"""\myextractref{%d}{%s}""" %(j, cmd) +"\n")
                    if do_amseqref:
                        f.write(r"""
\let\lppoldeqref\eqref
\def\eqref#1{%
  \ref{#1} % set in \tmp@save
  \begingroup
    \edef\ref##1{\detokenize\expandafter{\tmp@save}}
    \protected@xdef\tmp@save@eqref{\lppoldeqref{#1}}
  \endgroup
}
\def\myextractamseqref#1#2{
  #2
  \message{^^J*!*!*!*!LATEXPP:fixes.ref:ams-eqref:#1:{\detokenize\expandafter{\tmp@save@eqref}}!*!*!*!*}
}
""")
                        for j, cmd in enumerate(self.collected_cmds['ams-eqref']):
                            logger.debug("using cmd = %s", cmd)
                            f.write(r"""\myextractamseqref{%d}{%s}""" %(j, cmd) +"\n")
                    f.write(r"""\endgroup""" + "\n")

                # DO CLEVEREF REFERENCES
                if do_cleveref:
                    f.write(r"""
\begingroup
\makeatletter
\def\MakeUppercase{\noexpand\protect\noexpand\MakeUppercase}
\def\MakeLowercase{\noexpand\protect\noexpand\MakeLowercase}

\def\myextractcref#1#2{
  \def\tmp@save{}
  #2
  \message{^^J*!*!*!*!LATEXPP:fixes.ref:cleveref:#1:{\tmp@save}!*!*!*!*}
}
\def\addto@cref@tmp@save#1{%
  \begingroup
    \protected@edef\x{#1}%
    \xdef\tmp@save{\tmp@save\detokenize\expandafter{\x}}%
  \endgroup
}
\def\@setcref@pairgroupconjunction{\addto@cref@tmp@save\crefpairgroupconjunction}%
\def\@setcref@middlegroupconjunction{\addto@cref@tmp@save\crefmiddlegroupconjunction}%
\def\@setcref@lastgroupconjunction{\addto@cref@tmp@save\creflastgroupconjunction}%
\def\@@@setnamecref#1#2{%
  \expandafter\def\expandafter\@tempa\expandafter{#1}%
  \addto@cref@tmp@save{\expandafter#2\@tempa}%
}%
""")

                    no_hyperlink_code = r"""
\def\@@@setcref#1#2{%
  \cref@getlabel{#2}{\@templabel}#1{\@templabel}{}{}%
  \addto@cref@tmp@save{#1{\@templabel}{}{}}%
}
\def\@@@setcrefrange#1#2#3{%
  \cref@getlabel{#2}{\@labela}%
  \cref@getlabel{#3}{\@labelb}%
  \addto@cref@tmp@save{#1{\@labela}{\@labelb}{}{}{}{}}%
}
\def\@@@setcpageref#1#2{%
  \cpageref@getlabel{#2}{\@temppage}%
  \addto@cref@tmp@save{#1{\@temppage}{}{}}%
}
\def\@@@setcpagerefrange#1#2#3{%
  \cpageref@getlabel{#2}{\@pagea}%
  \cpageref@getlabel{#3}{\@pageb}%
  \addto@cref@tmp@save{#1{\@pagea}{\@pageb}{}{}{}{}}%
}
"""
                    # cleveref.sty 2018/03/27 lines 2215->
                    with_hyperlink_code = r"""
\def\lpp@cref@hyperlink#1#2#3\@nil{%
  % #1 = url, #2 = target, #3 = link text  -- (?)
  \if\relax\detokenize\expandafter{#1}\relax% empty URL
    \protect\hyperlink{#2}{#3}%
  \else
    \if\relax\detokenize\expandafter{#2}\relax% empty target
      \protect\href{#1}{#3}%
    \else
      \protect\hyperref{#1}{}{#2}{#3}%
    \fi
  \fi
}%  %\protect\hyperlink[#2]{#3}}
    \def\@@@setcref#1#2{%
      \cref@getlabel{#2}{\@templabel}%
      \if@crefstarred%
        \addto@cref@tmp@save{#1{\@templabel}{}{}}%
      \else%
        \edef\@tempname{\cref@hyperlinkname{#2}}%
        \edef\@tempurl{\cref@hyperlinkurl{#2}}%
        \addto@cref@tmp@save{#1{\@templabel}{\lpp@cref@hyperlink{\@tempurl}{\@tempname}}{\@nil}}%
      \fi}%
    \def\@@@setcrefrange#1#2#3{%
      \cref@getlabel{#2}{\@labela}%
      \cref@getlabel{#3}{\@labelb}%
      \if@crefstarred%
        \addto@cref@tmp@save{#1{\@labela}{\@labelb}{}{}{}{}}%
      \else%
        \edef\@tempnamea{\cref@hyperlinkname{#2}}%
        \edef\@tempurlb{\cref@hyperlinkurl{#3}}%
        \edef\@tempnameb{\cref@hyperlinkname{#3}}%
        \edef\@tempurla{\cref@hyperlinkurl{#2}}%
        \addto@cref@tmp@save{#1{\@labela}{\@labelb}%
          {\lpp@cref@hyperlink{\@tempurla}{\@tempnamea}}{\@nil}%
          {\lpp@cref@hyperlink{\@tempurlb}{\@tempnameb}}{\@nil}%
        }
      \fi}%
    \def\@@@setcpageref#1#2{%
      \cpageref@getlabel{#2}{\@temppage}%
      \if@crefstarred%
        \addto@cref@tmp@save{#1{\@temppage}{}{}}%
      \else%
        \edef\@tempname{\cref@hyperlinkname{#2}}%
        \edef\@tempurl{\cref@hyperlinkurl{#2}}%
        \addto@cref@tmp@save{#1{\@temppage}{\lpp@cref@hyperlink{\@tempurl}{\@tempname}}{\@nil}}%
      \fi}%
    \def\@@@setcpagerefrange#1#2#3{%
      \cpageref@getlabel{#2}{\@pagea}%
      \cpageref@getlabel{#3}{\@pageb}%
      \if@crefstarred%
        \addto@cref@tmp@save{#1{\@pagea}{\@pageb}{}{}{}{}}%
      \else%
        \edef\@tempnamea{\cref@hyperlinkname{#2}}%
        \edef\@tempurlb{\cref@hyperlinkurl{#3}}%
        \edef\@tempnameb{\cref@hyperlinkname{#3}}%
        \edef\@tempurla{\cref@hyperlinkurl{#2}}%
        \addto@cref@tmp@save{#1{\@pagea}{\@pageb}%
          {\lpp@cref@hyperlink{\@tempurla}{\@tempnamea}}{\@nil}%
          {\lpp@cref@hyperlink{\@tempurlb}{\@tempnameb}}{\@nil}%
        }
      \fi}%
"""

                    if not self.make_hyperlinks:
                        f.write(no_hyperlink_code)
                    else:
                        f.write(r"""
\ifLatexppRefUseHyperref
""" + with_hyperlink_code + r"""
\else
""" + no_hyperlink_code + r"""
\fi
""")

                    for j, cmd in enumerate(self.collected_cmds['cleveref']):
                        logger.debug("using cmd = %s", cmd)
                        f.write(r"""\myextractcref{%d}{%s}"""%(j, cmd) + "\n")
                    f.write(r"""\endgroup""" + "\n")

                f.write(r"""\end{document}""" + "\n")

            if self.debug_latex_output:
                with open(os.path.join(tmpdirname, 'tmp.tex')) as f:
                    logger.debug("TEMP LATEX FILE is =\n%s", f.read())

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

            if self.debug_latex_output:
                logger.debug("Ran latex, output =\n%s%s",
                             res.stdout.decode('utf-8'), res.stderr.decode('utf-8'))

            out = res.stdout.decode('utf-8')
            lwout = self.lpp.make_latex_walker(out)

            rx_magic = re.compile(r'\*\!\*\!\*\!\*\!LATEXPP:fixes\.ref:(?P<reftype>[\w_-]+):'+
                                  r'(?P<cmd_id>\d+):')

            resolved_cmds_for_index = { r: {}  for r in self.ref_types }

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

                resolved_cmds_for_index[m.group('reftype')][int(m.group('cmd_id'))] = the_expansion
                
            self.resolved_cmds = {reftype:
                                  {self.collected_cmds[reftype][i]: v
                                   for i, v in resolved_cmds_for_index[reftype].items()}
                                  for reftype in self.ref_types}
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



