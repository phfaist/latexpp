import re
import yaml
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, std_macro, \
    ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.macro_subst_helper import MacroSubstHelper


# parse entropy macros etc.


_thmsets = yaml.safe_load("""
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


class QitObjectFixes(object):
    
    def __init__(self, qitobjs=dict(), thmsets=['stdset'],
                 HSym='H', DSym='D', DCSym=r'\hat{D}'):
        self.qitobjs = dict(baseqitobjs)
        for tsetname in thmsets:
            self.qitobjs.update(_thmsets[tsetname])
        self.qitobjs.update(qitobjs)
        self.HSym = HSym
        self.DSym = DSym
        self.DCSym = DCSym

    def specs(self):
        return dict(macros= (
            MacroSpec(mname, args_parser=PhfQitObjectArgsParser(self.qitargspec(m['type'])))
            for mname, m in self.qitobjs.items()
        ) )

    def qitargspec(self, t):
        return {
            "IdentProc": "`[[{",
            "ee": "^",
            "Hbase": "`[[{[",
            "Hfnbase": "`(",
            "DD": "_^`{{",
            "Dbase": "[`{{",
            "DCohbase": "[`{{{{{",
        }.get(t)


    def fix_node(self, n, lpp):
        
        if not n.isNodeType(latexwalker.LatexMacroNode) or n.macroname not in self.qitobjs:
            return None

        m = self.qitobjs[n.macroname]

        return self.fix_qitobj(m, n, lpp)



    def fix_qitobj(self, m, n, lpp):

        if m['type'] == 'IdentProc':

            nsizespec, nsysA, nsysB, narg = n.nodeargd.argnlist
            sym = m.get('sym', r'\mathrm{id}')

            subscript = ''
            A, B = '', ''
            if nsysA is not None:
                A = lpp.latexpp_group_contents(nsysA)
            if nsysB is not None:
                B = lpp.latexpp_group_contents(nsysB)
            if A:
                if B:
                    subscript = A + r'\to ' + B
                else:
                    subscript = A

            text = '{' + sym + '}'
            if subscript:
                text += '_{' + subscript + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '|', ')')
            text += od + lpp.latexpp_group_contents(narg) + cd
            return text

        if m['type'] == 'ee':

            narg, = n.nodeargd.argnlist
            sym = m.get('sym', r'e')

            return '{'+sym+'}^{' + lpp.latexpp_group_contents(narg) + '}'
        
        if m['type'] == 'Hbase':

            nsizespec, nstate, nepsilon, ntargetsys, ncondsys = n.nodeargd.argnlist
            sym = m.get('sym', self.HSym)
            sub = m.get('sub', None)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if nepsilon is not None:
                text += '^{' + lpp.latexpp_group_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '|', ')')
            text += od
            text += lpp.latexpp_group_contents(ntargetsys)
            if ncondsys is not None:
                text += r'\,' + md + r'\,' + lpp.latexpp_group_contents(ncondsys)
            text += cd
            if nstate is not None:
                text += r'_{' + lpp.latexpp_group_contents(nstate) + '}'
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
            (od, md, cd) = self._delims(nsizespec, '(', '|', ')')
            text += od + lpp.latexpp_group_contents(narg) + cd
            return text

        if m['type'] == 'Dbase':
            
            nepsilon, nsizespec, nstate, nrel = n.nodeargd.argnlist
            sub = m.get('sub', None)
            sym = m.get('sym', self.DSym)

            text = '{' + sym + '}'
            if sub:
                text += '_{' + sub + '}'
            if nepsilon is not None:
                text += '^{' + lpp.latexpp_group_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', r'\Vert', ')')
            text += od + lpp.latexpp_group_contents(nstate) + r'\,' + md + r'\,' \
                + lpp.latexpp_group_contents(nrel) + cd
            return text

        if m['type'] == 'DD':
            
            nsub, nsup, nsizespec, nstate, nrel = n.nodeargd.argnlist
            sym = m.get('sym', self.DSym)

            text = '{' + sym + '}'
            if nsub is not None:
                text += '_{' + lpp.latexpp_group_contents(nsub) + '}'
            if nsup is not None:
                text += '^{' + lpp.latexpp_group_contents(nsup) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', r'\Vert', ')')
            text += od + lpp.latexpp_group_contents(nstate) + r'\,' + md + r'\,' \
                + lpp.latexpp_group_contents(nrel) + cd
            return text

        if m['type'] == 'DCohbase':

            nepsilon, nsizespec, nstate, nX, nXp, nGX, nGXp = n.nodeargd.argnlist
            sym = m.get('sym', self.DCSym)
            process_arg_subscripts = m.get('process_arg_subscripts', False)

            text = '{' + sym + '}'

            tX = lpp.latexpp_group_contents(nX)
            tXp = lpp.latexpp_group_contents(nXp)
            if tX and tXp:
                text += '_{' + tX + r'\to ' + tXp + '}'
            elif tX:
                text += '_{' + tX + '}'
            elif tXp:
                text += '_{' + tXp + '}'

            if nepsilon is not None:
                text += '^{' + lpp.latexpp_group_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', r'\Vert', ')')
            if nstate.isNodeType(latexwalker.LatexGroupNode) and \
               len(nstate.nodelist) and nstate.nodelist[0].isNodeType(latexwalker.LatexCharsNode) and \
               nstate.nodelist[0].chars.lstrip().startswith('*'):
                statelatex = lpp.latexpp_group_contents(nstate).lstrip(' \t*') # remove '*'
            else:
                if process_arg_subscripts:
                    statelatex = lpp.latexpp_group_contents(nstate) + '_{' \
                        + tX + r'\to ' + tXp + '}'
                else:
                    statelatex = lpp.latexpp_group_contents(nstate) + '_{' + tXp \
                        + 'R_{' + tX + '}}'
            text += od + statelatex + r'\,' + md + r'\,' + lpp.latexpp_group_contents(nGX) + r',\,' \
                + lpp.latexpp_group_contents(nGXp) + cd
            return text

        raise ValueError("Unknown phfqit macro type: {!r}".format(m))


    def _delims(self, sizenode, opendelim, middelim, closedelim):
        if sizenode is None:
            return (opendelim, middelim, closedelim)
        if sizenode.isNodeType(latexwalker.LatexCharsNode) and sizenode.chars == '*':
            return (r'\mathopen{}\left'+opendelim,
                    r'\mathclose{}\middle'+middelim+r'\mathopen{}',
                    r'\right'+closedelim+r'\mathclose{}')
        if sizenode.isNodeType(latexwalker.LatexMacroNode):
            mname = sizenode.macroname
            return (r'\mathopen{}'+'\\'+mname+'l'+opendelim,  # \bigl(
                    r'\mathopen{}'+'\\'+mname+middelim,  # \big|
                    r'\mathopen{}'+'\\'+mname+closedelim) # \bigr)

        raise ValueError("unexpected optional sizing node : "+repr(sizenode))








mathtools_delims_macros = {
    'abs': (r'\lvert', r'\rvert'),
    'norm': (r'\lVert', r'\rVert'),
    'avg': (r'\langle', r'\rangle'),

    'ket': (r'\lvert', r'{%(1)s}', r'\rangle'),
    'bra': (r'\langle', r'{%(1)s}', r'\rvert'),
    'braket': (r'\langle', r'{%(1)s}\hspace*{0.2ex}%(delimsize)s\vert\hspace*{0.2ex}{%(2)s}',
               r'\rangle'),
    'ketbra': (r'\lvert', r'{%(1)s}%(delimsize)s\rangle\hspace*{-0.25ex}%(delimsize)s\langle{%(2)s}',
               r'\rvert'),
    'proj': (r'\lvert', r'{%(1)s}%(delimsize)s\rangle\hspace*{-0.25ex}%(delimsize)s\langle{%(1)s}',
             r'\rvert'),
    
    'matrixel': (r'\langle',
                 r'{%(1)s}\hspace*{0.2ex}%(delimsize)s\vert\hspace*{0.2ex}{%(2)s}'
                 +r'\hspace*{0.2ex}%(delimsize)s\vert\hspace*{0.2ex}{%(3)s}',
                 r'\rangle'),
    'dmatrixel': (r'\langle',
                  r'{%(1)s}\hspace*{0.2ex}%(delimsize)s\vert\hspace*{0.2ex}{%(2)s}'
                 +r'\hspace*{0.2ex}%(delimsize)s\vert\hspace*{0.2ex}{%(1)s}',
                  r'\rangle'),
    'innerprod': (r'\langle',
                  r'{%(1)s},\hspace*{0.2ex}{%(2)s}',
                  r'\rangle'),

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

class MacrosFixes:
    def __init__(self, *,
                 subst={}, ops={}, delims={},
                 math_operator_fmt=r'\operatorname{%(opname)s}',
                 subst_use_hspace=True):
        the_simple_substitution_macros = dict(simple_substitution_macros)
        the_simple_substitution_macros.update(subst)
        # remove any items which have a None value (used to indicate a default
        # key should be removed from the YAML config)

        the_math_operators = dict(math_operators)
        the_math_operators.update(ops)
        the_simple_substitution_macros.update(**{
            opname: math_operator_fmt%dict(opname=opv)
            for opname, opv in the_math_operators.items()
        })

        # delimiter macros --> substitution rules
        self.mathtools_delims_macros = dict(mathtools_delims_macros)
        self.mathtools_delims_macros.update(delims)
        _delempties(self.mathtools_delims_macros)

        def delim_cfg(delimtuple):
            if len(delimtuple) == 2:
                return dict(qitargspec='*[{',
                            repl=r'%(open_delim)s{%(1)s}%(close_delim)s')
            numargs = max( int(m.group(1)) for m in re.finditer(r'\%\((\d)\)s', delimtuple[1]) )
            return dict(qitargspec='*[' + '{'*numargs,
                        repl='%(open_delim)s' + delimtuple[1] + '%(close_delim)s')

        the_simple_substitution_macros.update(**{
            mname: delim_cfg(delimtuple)
            for mname, delimtuple in self.mathtools_delims_macros.items()
        })

        _delempties(the_simple_substitution_macros)


        # remove \hspace...'s if we don't want them.
        # Iterate over copy of dict because we modify it
        if not subst_use_hspace:
            for mname, mcfg in the_simple_substitution_macros.copy().items():
                if isinstance(mcfg, str):
                    the_simple_substitution_macros[mname] = rx_hspace.sub('', mcfg)
                else:
                    the_simple_substitution_macros[mname]['repl'] = \
                        rx_hspace.sub('', mcfg['repl'])


        self.substitution_helper = MacroSubstHelper(
            macros=the_simple_substitution_macros,
            argspecfldname='qitargspec',
            args_parser_class=PhfQitObjectArgsParser,
        )



    def specs(self):
        # get specs from substitution helper
        return dict(**self.substitution_helper.get_specs())

    def fix_node(self, n, lpp):

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
                
                if n.nodeargd.argnlist[0] is not None:
                    # with star
                    delims_pc = (r'\mathopen{}\left%s', r'\right%s\mathclose{}')
                    delimsize = r'\middle'
                elif n.nodeargd.argnlist[1] is not None:
                    sizemacro = '\\'+n.nodeargd.argnlist[1].nodelist[0].macroname
                    delimsize = sizemacro
                    delims_pc = (sizemacro+r'l%s', sizemacro+r'r%s')
                else:
                    delims_pc = ('%s', '%s')
                    delimsize = ''

                # get delim specification for this macro
                delimchars = list(self.mathtools_delims_macros[n.macroname])
                if len(delimchars) == 3:
                    # replacement string is already stored in substitution helper
                    delimchars = [delimchars[0], delimchars[2]]

                # ensure we protect bare delimiter macros with a trailing space
                for j in (0, 1):
                    if re.match(r'^\\[a-zA-Z]+$', delimchars[j]): # bare macro, protect with space
                        delimchars[j] = delimchars[j] + ' '

                context = dict(open_delim=delims_pc[0]%delimchars[0],
                               delimsize=delimsize,
                               close_delim=delims_pc[1]%delimchars[1])
                return self.substitution_helper.eval_subst(c, n, lpp,
                                                           argoffset=2,
                                                           context=context)

            return self.substitution_helper.eval_subst(c, n, lpp)
                

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
        return "{}(qitargspec={!r}, argnlist={!r})".format(self.__class__.__name__,
                                                           self.qitargspec,
                                                           self.argnlist)


class PhfQitObjectArgsParser(MacroStandardArgsParser):

    def __init__(self, qitargspec):

        self.qitargspec = qitargspec
        argspec = qitargspec_to_argspec(self.qitargspec)

        super().__init__(argspec=argspec)

    def parse_args(self, w, pos, parsing_context=None):

        if parsing_context is None:
            parsing_context = latexwalker.ParsingContext()

        argnlist = []

        p = pos

        for argt in self.qitargspec:

            #
            # copied from MacroStandardArgsParser
            #

            if argt == '{':
                (node, np, nl) = w.get_latex_expression(p, strict_braces=False,
                                                        parsing_context=parsing_context)
                p = np + nl
                argnlist.append(node)

            elif argt == '[':

                if self.optional_arg_no_space and w.s[p].isspace():
                    # don't try to read optional arg, we don't allow space
                    argnlist.append(None)
                    continue

                optarginfotuple = w.get_latex_maybe_optional_arg(p, parsing_context=parsing_context)
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
                    argnlist.append(
                        w.make_node(latexwalker.LatexCharsNode, chars='*', pos=tok.pos, len=tok.len)
                    )
                    p = tok.pos + 1
                else:
                    argnlist.append(None)

            elif argt == '`':

                # optional size arg introduced by "`"

                tok = w.get_token(p)

                #print("*** READING OPTIONAL SIZE ARG ... tok=", repr(tok))
                
                if tok.tok in ('char', 'specials') and \
                   (tok.arg == '`' or getattr(tok.arg, 'specials_chars', None) == '`'):
                    # we have an optional size arg
                    p = tok.pos+1

                    #print("... YES")

                    tok = w.get_token(p)

                    # check for star
                    if tok.tok == 'char' and tok.arg == '*':
                        # has star
                        argnlist.append(
                            w.make_node(latexwalker.LatexCharsNode, chars='*', pos=tok.pos, len=tok.len)
                        )
                        p = tok.pos + 1
                    elif tok.tok == 'macro':
                        argnlist.append(
                            w.make_node(latexwalker.LatexMacroNode, macroname=tok.arg, nodeargd=None,
                                        pos=tok.pos, len=tok.len)
                        )
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
                                                                 parsing_context=parsing_context)
                argnlist.append( argnode )
                p = ppos+plen

            elif argt in ('_', '^'):
                
                # optional size arg introduced by "_" or "^"

                tok = w.get_token(p)

                # check for star
                if tok.tok == 'char' and tok.arg == argt:
                    # has this argument, read expression:
                    p = tok.pos+tok.len
                    (node, np, nl) = w.get_latex_expression(p, strict_braces=False,
                                                            parsing_context=parsing_context)
                    p = np + nl
                    argnlist.append(node)

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


