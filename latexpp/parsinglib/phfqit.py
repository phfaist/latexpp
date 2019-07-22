
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, ParsedMacroArgs, MacroStandardArgsParser
from pylatexenc import latexwalker


# parse entropy macros etc.


class Fixes(object):
    
    def __init__(self):
        self.macros = {}

        self._def_Hbase('Hmin', r'\mathrm{min}')
        self._def_Hbase('HH', None)
        self._def_Hbase('Hzero', r'0')
        self._def_Hbase('Hmaxf', r'\mathrm{max}')

        self._def_Hfnbase('Hfn', None, None)

        self._def_Dbase('Dmax', r'\mathrm{max}')
        self._def_Dbase('Dminz', r'0')
        self._def_Dbase('Dminf', r'\mathrm{min}')
        self._def_Dbase('Dr', r'\mathrm{Rob}')
        self._def_Dbase('DHyp', r'\mathrm{H}')
        self._def_Dbase('Dhyp', r'\mathrm{h}')

        self._def_DCohbase('DCohx')
        self._def_DCohbase('DCohz')

        self.macros['DD'] = {
            'spec': MacroSpec('DD', args_parser=PhfQitObjectArgsParser("_^`{{")),
            'type': 'DD',
            'p': ( 'D', )
        }

    def iter_macro_specs(self):
        return ( m['spec'] for mname, m in self.macros.items() )

    def _def_Hbase(self, mname, sub, sym='H'):
        self.macros[mname] = {
            'spec': MacroSpec(mname, args_parser=PhfQitObjectArgsParser("`[[{[")),
            'type': 'Hbase',
            'p': (sub, sym)
        }

    def _def_Hfnbase(self, mname, sub, sup, sym='H'):
        self.macros[mname] = {
            'spec': MacroSpec(mname, args_parser=PhfQitObjectArgsParser("`(")),
            'type': 'Hfnbase',
            'p': (sub, sup, sym),
        }

    def _def_Dbase(self, mname, sub, sym='D'):
        self.macros[mname] = {
            'spec': MacroSpec(mname, args_parser=PhfQitObjectArgsParser("[`{{")),
            'type': 'Dbase',
            'p': (sub, sym),
        }

    def _def_DCohbase(self, mname, sym=r'\hat{D}'):
        self.macros[mname] = {
            'spec': MacroSpec(mname, args_parser=PhfQitObjectArgsParser("[`{{{{{")),
            'type': 'DCohbase',
            'p': (sym,)
        }


    def fix_node(self, n, latexpp):
        
        if not n.isNodeType(latexwalker.LatexMacroNode) or n.macroname not in self.macros:
            return None

        def latexpp_contents(n):
            if n.isNodeType(latexwalker.LatexGroupNode):
                return latexpp(n.nodelist)
            return latexpp(n)

        m = self.macros[n.macroname]

        if m['type'] == 'Hbase':

            nsizespec, nstate, nepsilon, ntargetsys, ncondsys = n.nodeargd.argnlist

            text = '{' + m['p'][1] + '}'
            if m['p'][0]:
                text += '_{' + m['p'][0] + '}'
            if nepsilon is not None:
                text += '^{' + latexpp_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '|', ')')
            text += od
            text += latexpp_contents(ntargetsys)
            if ncondsys is not None:
                text += md
                text += latexpp_contents(ncondsys)
            text += cd
            return text
        
        if m['type'] == 'Hfnbase':
            
            nsizespec, narg = n.nodeargd.argnlist

            text = '{' + m['p'][2] + '}'
            if m['p'][0]:
                text += '_{' + m['p'][0] + '}'
            if m['p'][1]:
                text += '^{' + m['p'][1] + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '|', ')')
            text += od
            text += latexpp_contents(narg)
            text += cd
            return text

        if m['type'] == 'Dbase':
            
            nepsilon, nsizespec, nstate, nrel = n.nodeargd.argnlist

            text = '{' + m['p'][1] + '}'
            if m['p'][0]:
                text += '_{' + m['p'][0] + '}'
            if nepsilon is not None:
                text += '^{' + latexpp_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '\Vert', ')')
            text += od + latexpp_contents(nstate) + md + latexpp_contents(nrel) + cd
            return text

        if m['type'] == 'DD':
            
            nsub, nsup, nsizespec, nstate, nrel = n.nodeargd.argnlist

            text = '{' + m['p'][0] + '}'
            if nsub is not None:
                text += '_{' + latexpp_contents(nsub) + '}'
            if nsup is not None:
                text += '^{' + latexpp_contents(nsup) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '\Vert', ')')
            text += od + latexpp_contents(nstate) + md + latexpp_contents(nrel) + cd
            return text

        if m['type'] == 'DCohbase':

            nepsilon, nsizespec, nstate, nX, nXp, nGX, nGXp = n.nodeargd.argnlist

            text = '{' + m['p'][0] + '}'
            text += '_{' + latexpp_contents(nX) + r'\to ' + latexpp_contents(nXp) + '}'
            if nepsilon is not None:
                text += '^{' + latexpp_contents(nepsilon) + '}'
            (od, md, cd) = self._delims(nsizespec, '(', '\Vert', ')')
            if nstate.isNodeType(latexwalker.LatexGroupNode) and \
               len(nstate.nodelist) and nstate.nodelist[0].isNodeType(latexwalker.LatexCharsNode) and \
               nstate.nodelist[0].chars.lstrip().startswith('*'):
                statelatex = latexpp_contents(nstate).lstrip(' \t*') # remove '*'
            else:
                statelatex = latexpp_contents(nstate) + '_{' + latexpp_contents(nXp) \
                    + 'R_{' + latexpp_contents(nX) + '}}'
            text += od + statelatex + md + latexpp_contents(nGX) + ', ' + latexpp_contents(nGXp) + cd
            return text

        raise ValueError("Unknown phfqit macro type: {!r}".format(m))


    def _delims(self, sizenode, opendelim, middelim, closedelim):
        if sizenode is None:
            return (opendelim, middelim, closedelim)
        if sizenode.isNodeType(latexwalker.LatexCharsNode) and sizenode.chars == '*':
            return (r'\mathopen{}\left'+opendelim,
                    r'\mathclose{}\middle'+middelim+'\mathopen{}',
                    r'\right'+closedelim+r'\mathclose{}')
        if sizenode.isNodeType(latexwalker.LatexMacroNode):
            mname = sizenode.macroname
            return (r'\mathopen{}'+'\\'+mname+'l'+opendelim,  # \bigl(
                    r'\mathopen{}'+'\\'+mname+middelim,  # \big|
                    r'\mathopen{}'+'\\'+mname+closedelim) # \bigr)

        raise ValueError("unexpected optional sizing node : "+repr(sizenode))



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


