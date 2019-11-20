import re
import shlex
import logging

logger = logging.getLogger(__name__)


from pylatexenc import latexwalker

from .fix import BaseFix


# node.comment does not contain first '%' comment char
rx_lpp_pragma = re.compile(
    r'^%!(?P<nospace>\s*)lpp\s*(?P<instruction>[\}a-zA-Z_-]+)\s*(?P<rest>.*)$'
)


class PragmaFix(BaseFix):
    r"""
    A special kind of fix that processes latexpp pragma instructions.

    A `PragmaFix` differs from other :py:class:`~latexpp.fix.BaseFix`-based
    classes in how they process LaTeX nodes.  A `PragmaFix` subclass
    reimplements :py:func:`fix_pragma_scope()` and/or
    py:func:`fix_pragma_simple()`, which are called upon encountering
    ``%%!lpp <instruction> [<args>] [{ ... %%!lpp }]`` constructs.  The fix
    may then choose to process these pragma instructions, and their
    surrounding node lists, as it wishes.
    """

    def __init__(self):
        super().__init__()
    
    def fix_nodelist(self, nodelist):
        r"""
        Reimplemented from :py:`latexpp.fix.BaseFix`.  Subclasses should generally
        not reimplement this.
        """
        newnodelist = list(nodelist)

        for n in newnodelist:
            self.preprocess_child_nodes(n)

        self._do_pragmas(newnodelist)

        return newnodelist
    
    # override these to implement interesting functionality

    def fix_pragma_scope(self, nodelist, jstart, jend, instruction, args):
        r"""
        Called when a scoped pragma is encountered.  A scoped pragma is one with an
        opening brace at the end of the ``%%!lpp`` instruction, and is matched
        by a corresponding closing pragma instruction ``%%!lpp }``.

        This function may modify `nodelist` in place (including
        inserting/deleting elements).

        This function must return an index in `nodelist` where to continue
        processing of further pragmas after the current scope pragma.  For
        instance, the :py:class:`~latexpp.skip.SkipPragma` fix removes the
        entire scope pragma and its contents with ``nodelist[jstart:jend] = []``
        and then returns `jstart` to continue processing after the removed block
        (which has new index `jstart`).  (It is OK for this function to return
        an index that is larger than or equal to `len(nodelist)`; this is
        interpreted as there is no further content to process in `nodelist`.)

        Arguments:

          - `nodelist` is the full nodelist that is currently being processed.

          - `jstart` and `jend` are the indices in `nodelist` that point to the
            opening lpp pragma comment node and *one past* the closing lpp
            pragma comment node. This is like a Python range; for instance, you
            can remove the entire pragma block with ``nodelist[jstart:jend] =
            []``.

          - `instruction` is the pragma instruction name (the word after
            ``%%!lpp ``).

          - `args` is a list of any remaining arguments after the instruction
            (excluding the opening brace).

        Scope pragmas are parsed & reported inner first, then outer scopes.
        Nested scopes are allowed.  A pragma scope must be opened and closed
        within the same LaTeX scope (you cannot open a scope and close it in a
        different LaTeX environment, for instance).

        The default implementation does not do anything and returns `jend` to
        continue after the current pragma scope.
        """
        return jend

    def fix_pragma_simple(self, nodelist, j, instruction, args):
        r"""
        Called when a simple pragma is encountered.

        This function may modify `nodelist[j]` directly.  It can also modify the
        `nodelist` in place, including inserting/deleting elements if required.

        This function must return an index in `nodelist` where to continue
        processing of further pragmas after the current pragma.  (It is OK for
        this function to return an index that is larger than or equal to
        `len(nodelist)`; this is interpreted as there is no further content to
        process in `nodelist`.)

        Arguments:

          - `nodelist` is the full nodelist that is currently being processed.

          - `j` is the index in `nodelist` that points to the encountered lpp
            pragma comment node that this function might want to handle.

          - `instruction` is the pragma instruction name (the word after
            ``%%!lpp ``).

          - `args` is a list of any remaining arguments after the instruction.

        Simple pragmas are parsed & reported in linear order for each LaTeX
        scope (inner LaTeX scopes first).

        The default implementation does not do anything and returns `j+1` to
        continue processing after the current pragma.
        """
        return j+1


    def _do_pragmas(self, nodelist, jstart=0, stop_at_close_scope=False):

        j = jstart

        # we can modify nodelist in place.
        while j < len(nodelist):
            n = nodelist[j]
            md = self._parse_pragma(n)
            if md is None:
                j += 1
                continue

            instruction, rest = md

            args = shlex.split(rest)
            if instruction == '}':
                if stop_at_close_scope:
                    return j
                raise ValueError("Invalid closing pragma ‘%%!lpp }’ encountered "
                                 "at line {}, col {}"
                                 .format(*n.parsing_state.lpp_latex_walker
                                         .pos_to_lineno_colno(n.pos)))
            if args and args[-1] == '{':
                # this is a scope pragma
                j = self._do_scope_pragma(nodelist, j, instruction, args[:-1])
                continue
            else:
                # this is a single simple pragma
                j = self._do_simple_pragma(nodelist, j, instruction, args)
                continue

            j += 1

        if stop_at_close_scope:
            raise ValueError(
                "Cannot find closing ‘%%!lpp }’ to match ‘%%!lpp {}’ on line {}, col {}"
                .format(instruction,
                        *nodelist[jstart].parsing_state.lpp_latex_walker
                        .pos_to_lineno_colno(nodelist[jstart].pos))
            )

        return


    def _parse_pragma(self, node):
        if not node:
            return None
        if not node.isNodeType(latexwalker.LatexCommentNode):
            return None
        m = rx_lpp_pragma.match(node.comment)
        if not m:
            return None
        if m.group('nospace'):
            raise ValueError("LPP Pragmas should start with the exact string '%%!lpp': "
                             "‘{}’ @ line {}, col {}".format(
                                 n.to_latex(),
                                 *n.parsing_state.lpp_latex_walker
                                 .pos_to_lineno_colno(n.pos)
                             ))
        return m.group('instruction'), m.group('rest')
        
    def _do_scope_pragma(self, nodelist, j, instruction, args):
        
        # scan for closing pragma, parsing other pragmas on the way.
        jclose = self._do_pragmas(nodelist, j+1, stop_at_close_scope=True)

        # then fix this scope pragma
        jnew = self.fix_pragma_scope(nodelist, j, jclose+1, instruction, args)

        if jnew is None:
            raise RuntimeError(
                "Fix dealing with scope pragma ‘%%!lpp {}’ did not report new j position"
                .format( instruction )
            )

        return jnew

    def _do_simple_pragma(self, nodelist, j, instruction, args):

        jnew = self.fix_pragma_simple(nodelist, j, instruction, args)

        if jnew is None:
            raise RuntimeError(
                "Fix dealing with simple pragma ‘%%!lpp {}’ did not report new j position"
                .format( instruction )
            )

        return jnew

