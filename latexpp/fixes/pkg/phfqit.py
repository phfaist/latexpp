import re
import yaml
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.macro_subst_helper import MacroSubstHelper

from latexpp.fix import BaseFix


# parse entropy macros etc.


_qitobjdefs = yaml.safe_load(r"""
stdset:
  HH:
    type: Hbase
  Hzero:
    type: Hbase
    sub: '\mathrm{max},0'
  Hmin:
    type: Hbase
    sub: '\mathrm{min}'
  Hmaxf:
    type: Hbase
    sub: '\mathrm{max}'

  Hfn:
    type: Hfnbase

  Dmax:
    type: Dbase
    sub: '\mathrm{max}'
  Dminz:
    type: Dbase
    sub: '0'
  Dminf:
    type: Dbase
    sub: '\mathrm{min}'
  Dr:
    type: Dbase
    sub: '\mathrm{Rob}'
  DHyp:
    type: Dbase
    sub: '\mathrm{H}'
  Dhyp:
    type: Dbase
    sub: '\mathrm{h}'

  DCoh:
    type: DCohbase
  DCohx:
    type: DCohbase

  DD:
    type: DD
""")


baseqitobjs = yaml.safe_load("""
IdentProc:
  type: IdentProc
ee:
  type: ee
""")


_fixed_repl = {
    'DSym': lambda self: self.DSym,
    'HSym': lambda self: self.HSym,
}


class ExpandQitObjects(BaseFix):
    r"""
    Expand the definitions for the "QIT Objects" that are defined via the
    {phfqit} package.

    If applied along with :py:class:`latexpp.fixes.pkg.phfqit.ExpandMacros`, the
    dependency on package {phfqit} should be removed.

    Arguments:

    - `qitobjs`: a dictionary of custom "QIT Objects" to expand.  The dictionary
      has the structure ``{macroname: qitobjspec, ...}``, where:

      - `macroname` is the name of the macro representing this QIT object (no
        leading backslash);

      - `qitobjspec` is a dictionary with the following structure::

          {
            'type': <type>,
            'sym': <sym>
            <...>
          }

        The `<type>` is a string that must be one of the following QIT object
        types: 'Hbase', 'Hfnbase', 'DD', 'Dbase', 'DCohbase', 'IdentProc', 'ee'.
        This determines on one hand how the arguments to the macro are parsed
        and on the other hand the template latex code that will serve as a
        replacement for the QIT object invocation.
    
        The `<sym>` is any string that will be used to override the default
        symbol for this qit object type.  The 'sym' key can be left out to use
        the default symbol for the qit object.

        Depending on `<type>`, you can specify further keys that specify how the
        qit object is rendered (specified alongside `type: <type>` above, where
        `<...>` stands):

        - `<type>='Hbase'`: You may further specify ``'sub': <sub>`` which
          specifies the subscript to add to the entropy object.  This can be any
          LaTeX code.

        - `<type>='Hfnbase'`: You may further specify ``'sub': <sub>`` and
          ``'sup': <sup>`` which specifies the subscript and superscript to add
          to the entropy object.  Both can be any LaTeX code.

        - `<type>='Dbase'`: You may further specify ``'sub': <sub>`` which
          specifies the subscript to add to the relative entropy object.  This
          can be any LaTeX code.  You can also specify 'default_epsilon' to give
          a default value of the epsilon argument (any LaTeX code).

        - `<type>='Dalpha'`: You can also specify 'default_alpha' and
          'default_epsilon' to give a default value for these arguments (any
          LaTeX code).

        - `<type>='DD'`: There are no further keys you can specify.

        - `<type>='DCohbase'`: There are no further keys you can specify.
    
        - `<type>='IdentProc'`: There are no further keys you can specify.

        - `<type>='ee'`: There are no further keys you can specify.

    - `qitobjdef`: a list of built-in QIT object sets to use, designated by
      builtin set name.  Currently only the set named "stdset" is available,
      i.e., you may use ``qitobjdef=[]`` (don't use built-in QIT objects) or
      ``qitobjdef=['stdset']`` (use built-in QIT objects).

    - `HSym`: the default symbol to use for entropy-like QIT objects.  Defaults
      to 'H'

    - `DSym`: the default symbol to use for relative-entropy-like QIT objects.
      Defaults to 'D'

    - `DCSym`: the default symbol to use for coherent-relative-entropy-like QIT
      objects.  Defaults to '\\hat{D}'
    """
    
    def __init__(self, qitobjs=dict(), qitobjdef=['stdset'],
                 HSym='H', DSym='D', DCSym=r'\hat{D}'):
        super().__init__()

        self.qitobjs = dict(baseqitobjs)
        for qitobjname in qitobjdef:
            self.qitobjs.update(_qitobjdefs[qitobjname])
        self.qitobjs.update(qitobjs)
        self.HSym = HSym
        self.DSym = DSym
        self.DCSym = DCSym

    def specs(self, **kwargs):
        return dict(
            macros= (
                MacroSpec(mname, args_parser=PhfQitObjectArgsParser(self.qitargspec(m['type'])))
                for mname, m in self.qitobjs.items()
            )
        )

    def qitargspec(self, t):
        return {
            "IdentProc": "`[[{",
            "ee": "^",
            "Hbase": "`[[{[",
            "Hfnbase": "`(",
            "DD": "_^`{{",
            "Dbase": "[`{{",
            "Dalpha": "[[`{{",
            "DCohbase": "[`{{{{{",
        }.get(t)


    def fix_node(self, n, **kwargs):
        
        if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname in _fixed_repl:
            return _fixed_repl[n.macroname](self)

        if not n.isNodeType(latexwalker.LatexMacroNode) or n.macroname not in self.qitobjs:
            return None

        m = self.qitobjs[n.macroname]

        fixs = self.fix_qitobj(m, n)

        #logger.debug(" --> %r", fixs)

        return fixs



    def fix_qitobj(self, m, n):

        #logger.debug("fix_qitobj: m=%r, n=%r", m, n)

        if m['type'] == 'IdentProc':

            nsizespec, nsysA, nsysB, narg = n.nodeargd.argnlist
            sym = m.get('sym', r'\mathrm{id}')

            subscript = ''
            A, B = '', ''
            if nsysA is not None:
                A = self.preprocess_contents_latex(nsysA)
            if nsysB is not None:
                B = self.preprocess_contents_latex(nsysB)
            if A:
                if B:
                    subscript = A + r'\to ' + B
                else:
                    subscript = A

            text = '{' + sym + '}'
            if subscript:
                text += '_{' + subscript + '}'
            nargcontents = self.preprocess_contents_latex(narg)
            if nargcontents:
                (od, md, cd) = _delims(nsizespec, '(', '|', ')')
                text += od + nargcontents + cd
            return text

        if m['type'] == 'ee':

            narg, = n.nodeargd.argnlist
            sym = m.get('sym', r'e')

            return '{'+sym+'}^{' + self.preprocess_contents_latex(narg) + '}'
        
        if m['type'] == 'Hbase':

            nsizespec, nstate, nepsilon, ntargetsys, ncondsys = n.nodeargd.argnlist
            sym = m.get('sym', self.HSym)
            sub = m.get('sub', None)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if nepsilon is not None:
                text += '^{' + self.preprocess_contents_latex(nepsilon) + '}'
            (od, md, cd) = _delims(nsizespec, '(', '|', ')')
            text += od
            text += self.preprocess_contents_latex(ntargetsys)
            if ncondsys is not None:
                text += r'\,' + md + r'\,' + self.preprocess_contents_latex(ncondsys)
            text += cd
            if nstate is not None:
                text += r'_{' + self.preprocess_contents_latex(nstate) + '}'
            return text
        
        if m['type'] == 'Hfnbase':
            
            nsizespec, narg = n.nodeargd.argnlist
            sub = m.get('sub', None)
            sup = m.get('sup', None)
            sym = m.get('sym', self.HSym)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if sup:
                text += '^{' + sup + '}'
            nargcontents = self.preprocess_contents_latex(narg)
            if nargcontents:
                (od, md, cd) = _delims(nsizespec, '(', '|', ')')
                text += od + nargcontents + cd
            return text

        if m['type'] == 'Hfnbase':
            
            nsub, nsup, nsizespec, narg = n.nodeargd.argnlist
            sub = m.get('sub', None)
            sup = m.get('sup', None)
            sym = m.get('sym', self.HSym)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if sup:
                text += '^{' + sup + '}'
            nargcontents = self.preprocess_contents_latex(narg)
            if nargcontents:
                (od, md, cd) = _delims(nsizespec, '(', '|', ')')
                text += od + nargcontents + cd
            return text

        if m['type'] == 'Dbase':
            
            nepsilon, nsizespec, nstate, nrel = n.nodeargd.argnlist
            sub = m.get('sub', None)
            sym = m.get('sym', self.DSym)

            default_epsilon = m.get('default_epsilon', None)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if nepsilon is not None:
                text += '^{' + self.preprocess_contents_latex(nepsilon) + '}'
            elif default_epsilon:
                text += '^{' + default_epsilon + '}'
            (od, md, cd) = _delims(nsizespec, '(', r'\Vert', ')')
            nstatecontents = self.preprocess_contents_latex(nstate)
            nrelcontents = self.preprocess_contents_latex(nrel)
            if nstatecontents or nrelcontents:
                text += od + nstatecontents + r'\,' + md + r'\,' \
                    + nrelcontents + cd
            return text

        if m['type'] == 'Dalpha':
            
            nalpha, nepsilon, nsizespec, nstate, nrel = n.nodeargd.argnlist
            sym = m.get('sym', self.DSym)

            default_alpha = m.get('default_alpha', None)
            default_epsilon = m.get('default_epsilon', None)

            text = '{' + sym + '}'
            if nalpha is not None:
                text += '_{' + self.preprocess_contents_latex(nalpha) + '}'
            elif default_alpha:
                text += '_{' + default_alpha + '}'
            if nepsilon is not None:
                text += '^{' + self.preprocess_contents_latex(nepsilon) + '}'
            elif default_epsilon:
                text += '^{' + default_epsilon + '}'
            (od, md, cd) = _delims(nsizespec, '(', r'\Vert', ')')
            nstatecontents = self.preprocess_contents_latex(nstate)
            nrelcontents = self.preprocess_contents_latex(nrel)
            if nstatecontents or nrelcontents:
                text += od + nstatecontents + r'\,' + md + r'\,' \
                    + nrelcontents + cd
            return text

        if m['type'] == 'DD':
            
            nsub, nsup, nsizespec, nstate, nrel = n.nodeargd.argnlist
            sym = m.get('sym', self.DSym)

            text = '{' + sym + '}'
            if nsub is not None:
                text += '_{' + self.preprocess_contents_latex(nsub) + '}'
            if nsup is not None:
                text += '^{' + self.preprocess_contents_latex(nsup) + '}'
            (od, md, cd) = _delims(nsizespec, '(', r'\Vert', ')')
            nstatecontents = self.preprocess_contents_latex(nstate)
            nrelcontents = self.preprocess_contents_latex(nrel)
            if nstatecontents or nrelcontents:
                text += od + nstatecontents + r'\,' + md + r'\,' \
                    + nrelcontents + cd
            return text

        if m['type'] == 'DCohbase':

            nepsilon, nsizespec, nstate, nX, nXp, nGX, nGXp = n.nodeargd.argnlist
            sym = m.get('sym', self.DCSym)
            process_arg_subscripts = m.get('process_arg_subscripts', False)

            text = '{' + sym + '}'

            tX = self.preprocess_contents_latex(nX)
            tXp = self.preprocess_contents_latex(nXp)
            if tX and tXp:
                text += '_{' + tX + r'\to ' + tXp + '}'
            elif tX:
                text += '_{' + tX + '}'
            elif tXp:
                text += '_{' + tXp + '}'

            if nepsilon is not None:
                text += '^{' + self.preprocess_contents_latex(nepsilon) + '}'
            (od, md, cd) = _delims(nsizespec, '(', r'\Vert', ')')
            if nstate.isNodeType(latexwalker.LatexGroupNode) \
               and len(nstate.nodelist) \
               and nstate.nodelist[0].isNodeType(latexwalker.LatexCharsNode) \
               and nstate.nodelist[0].chars.lstrip().startswith('*'):
                # remove '*'
                statelatex = self.preprocess_contents_latex(nstate).lstrip(' \t*')
            else:
                if process_arg_subscripts:
                    statelatex = self.preprocess_contents_latex(nstate) + '_{' \
                        + tX + r'\to ' + tXp + '}'
                else:
                    statelatex = self.preprocess_contents_latex(nstate) + '_{' + tXp \
                        + 'R_{' + tX + '}}'
            text += od + statelatex + r'\,' + md + r'\,' + \
                self.preprocess_contents_latex(nGX) + r',\,' \
                + self.preprocess_contents_latex(nGXp) + cd
            return text

        raise ValueError("Unknown phfqit macro type: {!r}".format(m))


def _delims(sizenode, opendelim, middelim, closedelim):
    if sizenode is None:
        return (opendelim, middelim, closedelim)
    if sizenode.isNodeType(latexwalker.LatexGroupNode):
        assert( len(sizenode.nodelist) == 1 )
        sizenode = sizenode.nodelist[0]
    if sizenode.isNodeType(latexwalker.LatexCharsNode) and sizenode.chars == '*':
        return (r'\mathopen{}\left'+opendelim,
                r'\mathclose{}\middle'+middelim+r'\mathopen{}',
                r'\right'+closedelim+r'\mathclose{}')
    if sizenode.isNodeType(latexwalker.LatexMacroNode):
        mname = sizenode.macroname
        return (r'\mathopen{}'+'\\'+mname+'l '+opendelim,  # \bigl(
                r'\mathopen{}'+'\\'+mname+' '+middelim,  # \big|
                r'\mathopen{}'+'\\'+mname+'r '+closedelim) # \bigr)

    raise ValueError("unexpected optional sizing node : "+repr(sizenode))

def _delimtype(sizenode):
    if sizenode is None:
        return None
    if sizenode.isNodeType(latexwalker.LatexGroupNode):
        assert( len(sizenode.nodelist) == 1 )
        sizenode = sizenode.nodelist[0]
    if sizenode.isNodeType(latexwalker.LatexCharsNode) and sizenode.chars == '*':
        return '*'
    if sizenode.isNodeType(latexwalker.LatexMacroNode):
        return '\\'+sizenode.macroname




mathtools_delims_macros = {
    'abs': (r'\lvert', r'\rvert'),
    'norm': (r'\lVert', r'\rVert'),
    'avg': (r'\langle', r'\rangle'),

    'ket': (r'\lvert', r'{%(1)s}', r'\rangle'),
    'bra': (r'\langle', r'{%(1)s}', r'\rvert'),
    'braket': (r'\langle', r'{%(1)s}%(phfqitKetsBarSpace)s%(delimsize)s\vert%(phfqitKetsBarSpace)s{%(2)s}',
               r'\rangle'),
    'ketbra': (r'\lvert', r'{%(1)s}%(delimsize)s\rangle %(phfqitKetsRLAngleSpace)s%(delimsize)s\langle{%(2)s}',
               r'\rvert'),
    'proj': (r'\lvert', r'{%(1)s}%(delimsize)s\rangle %(phfqitKetsRLAngleSpace)s%(delimsize)s\langle{%(1)s}',
             r'\rvert'),
    
    'matrixel': (r'\langle',
                 r'{%(1)s}%(phfqitKetsBarSpace)s%(delimsize)s\vert %(phfqitKetsBarSpace)s{%(2)s}'
                 +r'%(phfqitKetsBarSpace)s%(delimsize)s\vert %(phfqitKetsBarSpace)s{%(3)s}',
                 r'\rangle'),
    'dmatrixel': (r'\langle',
                  r'{%(1)s}%(phfqitKetsBarSpace)s%(delimsize)s\vert %(phfqitKetsBarSpace)s{%(2)s}'
                 +r'%(phfqitKetsBarSpace)s%(delimsize)s\vert %(phfqitKetsBarSpace)s{%(1)s}',
                  r'\rangle'),
    'innerprod': (r'\langle',
                  r'{%(1)s}%(phfqitBeforeCommaSpace)s,%(phfqitAfterCommaSpace)s{%(2)s}',
                  r'\rangle'),

    'oket': (r'\lvert', r'{%(1)s}', r'\rrangle'),
    'obra': (r'\llangle', r'{%(1)s}', r'\rvert'),
    'obraket': (r'\llangle', r'{%(1)s}%(phfqitOKetsBarSpace)s%(delimsize)s\vert %(phfqitOKetsBarSpace)s{%(2)s}',
               r'\rrangle'),
    'oketbra': (r'\lvert', r'{%(1)s}%(delimsize)s\rrangle %(phfqitOKetsRLAngleSpace)s%(delimsize)s\llangle{%(2)s}',
               r'\rvert'),
    'oproj': (r'\lvert', r'{%(1)s}%(delimsize)s\rrangle %(phfqitOKetsRLAngleSpace)s%(delimsize)s\llangle{%(1)s}',
             r'\rvert'),
    
    'omatrixel': (r'\llangle',
                 r'{%(1)s}%(phfqitOKetsBarSpace)s%(delimsize)s\vert %(phfqitOKetsBarSpace)s{%(2)s}'
                 +r'%(phfqitOKetsBarSpace)s%(delimsize)s\vert %(phfqitOKetsBarSpace)s{%(3)s}',
                 r'\rrangle'),
    'odmatrixel': (r'\llangle',
                  r'{%(1)s}%(phfqitOKetsBarSpace)s%(delimsize)s\vert %(phfqitOKetsBarSpace)s{%(2)s}'
                 +r'%(phfqitOKetsBarSpace)s%(delimsize)s\vert %(phfqitOKetsBarSpace)s{%(1)s}',
                  r'\rrangle'),

    'intervalc': (r'[', r'{%(1)s\mathclose{},\mathopen{}%(2)s}', r']'),
    'intervalo': (r']', r'{%(1)s\mathclose{},\mathopen{}%(2)s}', r'['),
    'intervalco': (r'[', r'{%(1)s\mathclose{},\mathopen{}%(2)s}', r'['),
    'intervaloc': (r']', r'{%(1)s\mathclose{},\mathopen{}%(2)s}', r']'),

}

def gate(x):
    return r'\ifmmode\textsc{\lowercase{'+x+r'}}\else{\rmfamily\textsc{\lowercase{'+x+r'}}}\fi'

simple_substitution_macros = {
    r'Hs': r'\mathscr{H}',
    r'Ident': r'\mathds{1}',

    # bits and gates
    r'bit': {'qitargspec': '{', 'repl': r'\texttt{%(1)s}'},
    r'bitstring': {'qitargspec': '{', 'repl': r'\ensuremath{\underline{\overline{\texttt{%(1)s}}}}'},
    r'gate': {'qitargspec': '{',
              'repl': gate("%(1)s") },
    r'AND': gate('And'),
    r'XOR': gate('Xor'),
    r'CNOT': gate('C-Not'),
    r'NOT': gate('Not'),
    r'NOOP': gate('No-Op'),

    # math groups
    'uu': dict(qitargspec='(', repl=r'\mathrm{u}({%(1)s})'),
    'UU': dict(qitargspec='(', repl=r'\mathrm{U}({%(1)s})'),
    'su': dict(qitargspec='(', repl=r'\mathrm{su}({%(1)s})'),
    'SU': dict(qitargspec='(', repl=r'\mathrm{SU}({%(1)s})'),
    'so': dict(qitargspec='(', repl=r'\mathrm{so}({%(1)s})'),
    'SO': dict(qitargspec='(', repl=r'\mathrm{SO}({%(1)s})'),
    #'sl': dict(qitargspec='(', repl=r'\mathrm{sl}({%(1)s})'), # not in phfqit -- why? should add it there
    #'SL': dict(qitargspec='(', repl=r'\mathrm{SL}({%(1)s})'),
    'GL': dict(qitargspec='(', repl=r'\mathrm{GL}({%(1)s})'),
    'SN': dict(qitargspec='(', repl=r'\mathrm{S}_{%(1)s}'),
}
math_operators = {
    'tr': 'tr',
    'supp': 'supp',
    'rank': 'rank',
    'linspan': 'span',
    'spec': 'spec',
    'diag': 'diag',
    'Re': 'Re',
    'Im': 'Im',
    'poly': 'poly',
}

rx_hspace = re.compile(r'\\hspace\*?\{[^}]+\}')


def _delempties(d):
    delkeys = [k for k, v in d.items() if v is None]
    for k in delkeys:
        del d[k]

class ExpandMacros(BaseFix):
    r"""
    Expand various macros defined by the {phfqit} package.

    If applied along with :py:class:`latexpp.fixes.pkg.phfqit.ExpandQitObjects`,
    the dependency on package {phfqit} should be removed.

    Arguments:

    - `subst`: a dictionary of substitutions to perform.  The dictionary keys
      are macro names without leading backslash, and values are dictionaries of
      the form ``{'qitargspec': <qitargspec>, 'repl': <repl>}``.  This has a
      similar syntax to the :py:class:`latexpp.fixes.macro_subst.Subst` fix
      class, but argument parsing allows an extended syntax.  Instead of
      specifying an `'argspec': <argspec>`, you specify `'qitargspec':
      <qitargspec>` which provides argument parsing extensions to the usual
      `argspec`.

      Each character in `<qitargspec>` is one of:

      - '*', '[', '{' represent the same kind of arguments as for 'argspec' in
        :py:class:`latexpp.fixes.macro_subst.Subst`;

      - '(' represents a mandatory argument in parentheses;

      - '`' represents an optional argument introduced by ```<token or group>``;

      - '_' represents an optional argument introduced by ``_<token or group>``;

      - or '^' which represents an optional argument introduced by ``^<token or
        group>``.

      As for :py:class:`latexpp.fixes.macro_subst.Subst`, arguments are
      available in the replacement string `<repl>` via the syntax ``%(n)s``
      where `n` is the argument number.

      A default set of substitutions are provided according to the macros
      defined in the {phfqit} package; arguments here override the defaults.
      You can disable individual default substitutions by providingthe value
      `None` (`null` in the YAML file) for the given macro name in the `subst`
      dictionary.

    - `ops`: a dictionary of "operator names" to substitute for.  This is a
      dictionary ``{<opname>: <opstring>, ...}`` where `<opname>` is the macro
      name of the operator without leading backslash (e.g., ``tr`` for "trace"),
      and `<opstring>` is the replacement LaTeX string that will be formatted as
      an operator name.  See `math_operator_fmt=` for how operators are
      formatted.

      A default set of operator names are provided according to the macros
      defined in the {phfqit} package; arguments here override the defaults.
      You can disable individual default operator names by providing the value
      `None` (`null` in the YAML file) for the given operator name in the `ops`
      dictionary.

    - `math_operator_fmt`: The template string to use to format an operator.  By
      default, we use `\\operatorname{...}` to format the operator.  The
      template should contain the string `%(opname)s` which will be replaced by
      the actual operator name.  The default value is
      ``\operatorname{%(opname)s}``; if you prefer to use ``\mbox`` for
      operators, you could set this to ``\mbox{%(opname)s}``.

    - `delims`: A dictionary specifying macros that format delimited expressions
      (such as `\\abs`, `\\ket`, `\\norm`, etc.).  These macros take an optional
      star (which indicates that the delimiters should be latex-dynamically
      sized with ``\left`` and ``\right``), or an optional sizing macro in
      square braces (such as ``\norm[\big]{...}``).  After the optional star and
      optional argument, the macro must take a fixed number of mandatory
      arguments (e.g., one for ``\norm`` but two for ``\ketbra`` and three for
      ``\matrixel``).

      The `delims` argument is a dictionary ``{<delim-macro-name>: <delim-spec>,
      ...}`` where `<delim-macro-name>` is the name of the macro without leading
      backslash (e.g., 'ket' or 'abs').  The `<delim-spec>` is either:

      - `<delim-spec>=(<left-delim>, <right-delim>)`, i.e., a two-item tuple or
        list specifying the left and right delimiter.  The macro must take a
        single mandatory argument, which will be typeset between the two
        delimiters.  One must be able to size the delimiters using sizing
        commands such as ``\big`` or ``\left``/``\right``.

      - `<delim-spec>=(<left-delim>, <contents-repl>, <right-delim>)`, i.e., a
        three-item tuple or list.  The `<left-delim>` and `<right-delim>` are as
        above.  The `<contents-repl>` specifies how to format the contents
        between the two delimiters, and should contain replacement strings of
        the form ``%(n)s`` that expand into the `n`-th mandatory argument of the
        macro.  The number of mandatory arguments that the macro accepts is
        inferred by inspecting the replacement string and looking for the
        highest `n` in these replacement placeholders.  Furthermore, you can use
        the replacement placeholder ``%(delimsize)s``, which expands to the
        relevant sizing command (e.g., ``\big``, ``\middle`` to match
        ``\left``/``\right``, or nothing if no sizing options are given) and
        which can be placed immediately before a delimiter.

      - `<delim-spec>={'open': <left-delim>, 'close': <right-delim>, 'repl':
        <contents-repl>, 'default-size': r'\big', 'prefix': <prefix-content>,
        'suffix': <suffix-content>}` enables you to additional specify a default
        sizing argument if no size argument was specified, as well as additional
        fixed pieces of string to render before the opening delimiter (prefix)
        and after the closing delimiter (suffix).

    - `subst_use_hspace`: In all the above substitutions (including delimiters),
      there are some custom sizing corrections in the form of ``\hspace*{XXex}``
      that adjust the spacing between the different symbols in the expansion of
      those macros.  By default, they are kept in the replacement latex code so
      that the document looks the same when compiled.  If instead, you would
      like simple substitutions without these fine-tuning spacing commands, set
      `subst_use_hspace=False`.

    - `llanglefrommnsymbolfonts`: If set to `True`, then include preamble
      definitions that will make available the '\llangle' and '\rrangle'
      commands by picking the corresponding symbols from the MnSymbols
      font. (see https://tex.stackexchange.com/a/79701/32188)
    """

    def __init__(self, *,
                 subst=None, ops=None, delims=None,
                 math_operator_fmt=r'\operatorname{%(opname)s}',
                 subst_use_hspace=True,
                 subst_space=None,
                 llanglefrommnsymbolfonts=False,
                 ):
        super().__init__()

        if subst is None:
            subst = {}
        if ops is None:
            ops = {}
        if delims is None:
            delims = {}

        the_simple_substitution_macros = {}
        the_simple_substitution_macros.update(simple_substitution_macros)
        the_simple_substitution_macros.update(subst)
        # remove any items which have a None value (used to indicate a default
        # key should be removed from the YAML config)

        the_math_operators = {}
        the_math_operators.update(math_operators)
        the_math_operators.update(ops)
        the_simple_substitution_macros.update(**{
            opname: math_operator_fmt%dict(opname=opv)
            for opname, opv in the_math_operators.items()
        })

        # delimiter macros --> substitution rules
        the_mathtools_delims_macros = dict(mathtools_delims_macros)
        the_mathtools_delims_macros.update(delims)
        _delempties(the_mathtools_delims_macros)

        def mkdelimspec(delimspec):
            # delimspec = {
            #   'open': <left-delim>,
            #   'close': <right-delim>,
            #   'repl': <contents-repl>,
            #   'default-size': r'\big',
            #   'prefix': <prefix-content>,
            #   'suffix': <suffix-content>, }
            #   --> auto-set: 'qitargspec': <argspec>, 'full-repl': <full repl string>
            if isinstance(delimspec, (list, tuple)):
                if len(delimspec) == 2:
                    numargs = 1
                    delimspec = {
                        'open': delimspec[0],
                        'close': delimspec[1],
                        # set automatically below
                        # 'repl': r'%(open_delim)s{%(1)s}%(close_delim)s',
                        # 'qitargspec': '`*[{'
                    }
                else:
                    opendelim, repl, closedelim = delimspec
                    numargs = max( int(m.group(1))
                                   for m in re.finditer(r'\%\((\d)\)s', repl) )
                    delimspec = {
                        'open': opendelim,
                        'close': closedelim,
                        'repl': repl,
                        # set automatically below
                        # 'qitargspec': '`*[' + '{'*numargs
                    }
            if 'open' not in delimspec or 'close' not in delimspec:
                raise ValueError("<delim-spec> must contain keys 'open' and 'close': "
                                 + repr(delimspec))
            if 'default-size' not in delimspec:
                delimspec['default-size'] = None
            if 'repl' not in delimspec:
                delimspec['repl'] = r'{%(1)s}'
                delimspec['qitargspec'] = '`*[{'
            if 'qitargspec' not in delimspec:
                numargs = max( int(m.group(1))
                               for m in re.finditer(r'\%\((\d)\)s', delimspec['repl'] ) )
                delimspec['qitargspec'] = '`*[' + '{'*numargs
            if 'prefix' not in delimspec:
                delimspec['prefix'] = ''
            if 'suffix' not in delimspec:
                delimspec['suffix'] = ''

            delimspec['full-repl'] = (
                delimspec['prefix'] + r'%(open_delim)s'
                + delimspec['repl'] + 
                r'%(close_delim)s' + delimspec['suffix']
            )

            logger.debug("Parsed delimspec → ", delimspec)

            return delimspec

        self.mathtools_delims_macros = {
            k: mkdelimspec(v)
            for k, v in the_mathtools_delims_macros.items()
        }

        def delim_cfg(delimspec):
            return dict(qitargspec=delimspec['qitargspec'],
                        repl=delimspec['full-repl'])

        the_simple_substitution_macros.update(**{
            mname: delim_cfg(delimspec)
            for mname, delimspec in self.mathtools_delims_macros.items()
        })

        _delempties(the_simple_substitution_macros)


        self.subst_space = dict(
            phfqitKetsBarSpace=r'\mkern 1.5mu\relax ',
            phfqitKetsRLAngleSpace=r'\mkern -1.8mu\relax ',
            phfqitOKetsBarSpace=r'\mkern 1.5mu\relax ',
            phfqitOKetsRLAngleSpace=r'\mkern -1.8mu\relax ',
            phfqitKetsBeforeCommaSpace=r'',
            phfqitKetsAfterCommaSpace=r'\mkern 1.5mu\relax ',
        )
        if subst_space is not None:
            self.subst_space.update(subst_space)

        # remove \hspace...'s if we don't want them.
        if not subst_use_hspace:
            self.subst_space = {k: '' for k in self.subst_space.keys()}

        self.substitution_helper = MacroSubstHelper(
            macros=the_simple_substitution_macros,
            argspecfldname='qitargspec',
            args_parser_class=PhfQitObjectArgsParser,
        )

        self.llanglefrommnsymbolfonts = llanglefrommnsymbolfonts



    def specs(self, **kwargs):
        # get specs from substitution helper
        return dict(**self.substitution_helper.get_specs())

    def add_preamble(self):
        preamble = ""
        if self.llanglefrommnsymbolfonts:
            preamble += r"""
%% ---
%% Make the \llangle and \rrangle comands available by fetching
%% the corresponding symbols from the MnSymbols font.
%%
\DeclareFontFamily{OMX}{MnSymbolE}{}
\DeclareSymbolFont{MnLargeSymbols}{OMX}{MnSymbolE}{m}{n}
\SetSymbolFont{MnLargeSymbols}{bold}{OMX}{MnSymbolE}{b}{n}
\DeclareFontShape{OMX}{MnSymbolE}{m}{n}{
    <-6>  MnSymbolE5
   <6-7>  MnSymbolE6
   <7-8>  MnSymbolE7
   <8-9>  MnSymbolE8
   <9-10> MnSymbolE9
  <10-12> MnSymbolE10
  <12->   MnSymbolE12
}{}
\DeclareFontShape{OMX}{MnSymbolE}{b}{n}{
    <-6>  MnSymbolE-Bold5
   <6-7>  MnSymbolE-Bold6
   <7-8>  MnSymbolE-Bold7
   <8-9>  MnSymbolE-Bold8
   <9-10> MnSymbolE-Bold9
  <10-12> MnSymbolE-Bold10
  <12->   MnSymbolE-Bold12
}{}
\let\llangle\relax
\let\rrangle\relax
\DeclareMathDelimiter{\llangle}{\mathopen}%
                     {MnLargeSymbols}{'164}{MnLargeSymbols}{'164}
\DeclareMathDelimiter{\rrangle}{\mathclose}%
                     {MnLargeSymbols}{'171}{MnLargeSymbols}{'171}
%% ---
"""
        return preamble

    def fix_node(self, n, **kwargs):

        # we treat all via the substitution helper
        c = self.substitution_helper.get_node_cfg(n)
        if c is not None:

            # got a substitution. Check if it is a delimiter, which warrants
            # further processing
            if n.isNodeType(latexwalker.LatexMacroNode) and \
               n.macroname in self.mathtools_delims_macros:

                #
                # it's a delimiter macro!
                #

                # check for `backtick argument after checking for * and/or [,
                # because the latter have precedence

                delimtype = None
                if n.nodeargd.argnlist[1] is not None:
                    # with star
                    delimtype = '*'
                elif n.nodeargd.argnlist[2] is not None \
                     and n.nodeargd.argnlist[2].nodelist:
                    delimtype = '\\'+n.nodeargd.argnlist[2].nodelist[0].macroname
                elif n.nodeargd.argnlist[0] is not None:
                    # we have a backtick size
                    delimtype = _delimtype(n.nodeargd.argnlist[0])

                #
                # get delim specification for this macro
                #
                delimspec = self.mathtools_delims_macros[n.macroname]
                delimchars = [ delimspec['open'], delimspec['close'] ] # need list here

                if delimtype is None and delimspec['default-size'] is not None:
                    delimtype = delimspec['default-size']

                if delimtype is None:
                    delims_pc = ('%s', '%s')
                    delimsize = ''
                elif delimtype == '*':
                    # with star
                    delims_pc = (r'\mathopen{}\left %s', r'\right %s\mathclose{}')
                    delimsize = r'\middle'
                else:
                    sizemacro = delimtype
                    delimsize = sizemacro+r' '
                    delims_pc = (sizemacro+r'l %s', sizemacro+r'r %s')


                # ensure we protect bare delimiter macros with a trailing space
                for j in (0, 1):
                    if re.match(r'^\\[a-zA-Z]+$', delimchars[j]): # bare macro, protect with space
                        delimchars[j] = delimchars[j] + ' '

                context = dict(open_delim=delims_pc[0]%delimchars[0],
                               delimsize=delimsize,
                               close_delim=delims_pc[1]%delimchars[1],
                               **self.subst_space)
                return self.substitution_helper.eval_subst(
                    c,
                    n,
                    node_contents_latex=self.preprocess_contents_latex,
                    argoffset=3,
                    context=context
                )

            return self.substitution_helper.eval_subst(
                c,
                n,
                node_contents_latex=self.preprocess_contents_latex
            )
                

        return None




















# qitargspec: extension of argspec with:
#   *, [, {  --  as in latexwalker
#   ` -- optional size arg
#   ( -- mandatory arg in (...)
#   _ -- optional arg (subscript) that is marked by '_', e.g. \DD_{min}{...}{...}
#   ^ -- optional arg (superscript) that is marked by '^', e.g. \DD^{\epsilon}{...}{...}



def qitargspec_to_argspec(qitargspec):
    return "".join( x if x in ('*', '[', '{') else '['  for x in qitargspec )


class PhfQitObjectParsedArgs(ParsedMacroArgs):
    def __init__(self, qitargspec, argnlist, **kwargs):
        self.qitargspec = qitargspec

        argspec = qitargspec_to_argspec(self.qitargspec)

        super().__init__(argspec=argspec,
                         argnlist=argnlist,
                         **kwargs)
        
    def __repr__(self):
        return "{}(qitargspec={!r}, argnlist={!r})".format(
            self.__class__.__name__, self.qitargspec, self.argnlist
        )

    def args_to_latex(self, recomposer):
        return "".join(self._arg_to_latex(at, an, recomposer=recomposer)
                       for at, an in zip(self.qitargspec, self.argnlist))

    def _arg_to_latex(self, argt, argn, recomposer):
        if argn is None:
            return ''

        if argt == '{':
            return recomposer.node_to_latex(argn)
        elif argt == '[':
            return recomposer.node_to_latex(argn)
        elif argt == '*':
            return recomposer.node_to_latex(argn)
        elif argt == '`':
            return '`' + recomposer.node_to_latex(argn)
        elif argt == '(':
            return recomposer.node_to_latex(argn)
        elif argt in ('_', '^'):
            return argt + recomposer.node_to_latex(argn)
        
        raise RuntimeError("Invalid argt={!r} (argn={!r})".format(argt, argn))


class PhfQitObjectArgsParser(MacroStandardArgsParser):

    def __init__(self, qitargspec):

        self.qitargspec = qitargspec

        argspec = qitargspec_to_argspec(self.qitargspec)
        super().__init__(argspec=argspec)

    def parse_args(self, w, pos, parsing_state=None):

        if parsing_state is None:
            parsing_state = w.make_parsing_state()

        argnlist = []

        p = pos

        for argt in self.qitargspec:

            #
            # copied from MacroStandardArgsParser
            #

            if argt == '{':
                (node, np, nl) = w.get_latex_expression(p, strict_braces=False,
                                                        parsing_state=parsing_state)
                p = np + nl
                argnlist.append(node)

            elif argt == '[':

                if self.optional_arg_no_space and w.s[p].isspace():
                    # don't try to read optional arg, we don't allow space
                    argnlist.append(None)
                    continue

                optarginfotuple = w.get_latex_maybe_optional_arg(p, parsing_state=parsing_state)
                if optarginfotuple is None:
                    argnlist.append(None)
                    continue

                (node, np, nl) = optarginfotuple
                p = np + nl
                argnlist.append(node)

            elif argt == '*':
                # possible star.
                tok = w.get_token(p)
                if tok.tok == 'char' and tok.arg == '*':
                    # has star
                    node = w.make_node(latexwalker.LatexCharsNode,
                                       parsing_state=parsing_state,
                                       chars='*', pos=tok.pos, len=tok.len)
                    argnlist.append(node)
                    p = tok.pos + 1
                else:
                    argnlist.append(None)

            elif argt == '`':

                # optional size arg introduced by "`"

                tok = w.get_token(p)

                if tok.tok in ('char', 'specials') and \
                   (tok.arg == '`' or getattr(tok.arg, 'specials_chars', None) == '`'):
                    # we have an optional size arg
                    p = tok.pos+1

                    tok = w.get_token(p)

                    # check for star
                    if tok.tok == 'char' and tok.arg == '*':
                        # has star
                        thenode = w.make_node(latexwalker.LatexCharsNode,
                                              parsing_state=parsing_state,
                                              chars='*', pos=tok.pos, len=tok.len)
                        argnlist.append(thenode)
                        p = tok.pos + 1
                    elif tok.tok == 'macro':
                        thenode = w.make_node(latexwalker.LatexMacroNode,
                                              parsing_state=parsing_state,
                                              macroname=tok.arg,
                                              nodeargd=None,
                                              pos=tok.pos, len=tok.len)

                        argnlist.append(thenode)
                        p = tok.pos+tok.len
                    else:
                        raise latexwalker.LatexWalkerParseError(
                            msg="Expected '*' or macro after `",
                            s=w.s,
                            pos=p
                        )

                else:
                    # optional size arg not present
                    argnlist.append(None)

            elif argt == '(':

                (argnode, ppos, plen) = w.get_latex_braced_group(p, brace_type='(',
                                                                 parsing_state=parsing_state)
                argnlist.append( argnode )
                p = ppos+plen

            elif argt in ('_', '^'):
                
                # optional argument introduced by "_" or "^"

                tok = w.get_token(p)

                # check for intro char "_"/"^"
                if tok.tok == 'char' and tok.arg == argt:
                    # has this argument, read expression:
                    #optpos = tok.pos
                    p = tok.pos+tok.len
                    (node, np, nl) = w.get_latex_expression(p, strict_braces=False,
                                                            parsing_state=parsing_state)
                    p = np + nl
                    argnlist.append( node )
                    # argnlist.append(
                    #     w.make_node(
                    #         latexwalker.LatexGroupNode,
                    #         parsing_state=parsing_state,
                    #         nodelist=[ node ],
                    #         delimiters=(argt, ''),
                    #         pos=optpos,
                    #         len=np+nl-optpos
                    #     )
                    # )

                else:

                    argnlist.append(None)


            else:
                raise LatexWalkerError(
                    "Unknown macro argument kind for macro: {!r}".format(argt)
                )

        parsed = PhfQitObjectParsedArgs(
            qitargspec=self.qitargspec,
            argnlist=argnlist,
        )

        return (parsed, pos, p-pos)


