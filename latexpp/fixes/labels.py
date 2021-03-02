import re
import itertools
import hashlib
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fix import BaseMultiStageFix

from . import ref as lppfix_ref


_REFCMDS = dict(lppfix_ref._REFCMDS)
_REFCMDS.update({
    'autoref': {
        'autoref': {'macro': MacroSpec('autoref', args_parser=MacroStandardArgsParser('*{')),
                    'label_args': [1]},
    }
})


class RenameLabels(BaseMultiStageFix):
    r"""
    Detect labels pinned with \label{} and replace all future references in
    known referencing commands.

    Arguments:
    
      - `labelcmds`: a list of command names (without backslash) that have the
        same syntax as ``\label{}`` and that define label names.  (In the future
        I hope to be able to support alternative syntax, too, e.g., in
        tcolorbox's keyvals etc.)

      - `label_rename_fmt`: a python %-format string to generate the new label.
        Use fields of the type ``"%(prefix)s%(hash)s"`` or ``%(n)d``.  Keys can
        include `labelname` (earlier label name), ``n`` (a simple incremental
        counter for each label), ``hash`` (a hash of the earlier label),
        ``prefix`` (detects the prefix like "thm:" or "eq:", including colon,
        empty if no prefix).  [I will add more fields in the future probably.]

      - `ref_types`: which reference command types to recognize when replacing
        labels.  Here we use the same syntax as the
        :py:class:`latexpp.fixes.ref` filter.

      - `use_hash_length`: The key "%(hash)s" in `label_rename_fmt` computes the
        MD5 hash of the previous label and truncates its hexadecimal
        representation at `use_hash_length` chars.
    """
    def __init__(self, *,
                 labelcmds=['label'],
                 label_rename_fmt='%(prefix)s%(hash)s',
                 ref_types=None,
                 use_hash_length=16):

        super().__init__()

        self.labelcmds = labelcmds

        self.label_rename_fmt = label_rename_fmt

        if ref_types is None:
            ref_types = list(_REFCMDS.keys())

        self.ref_types = ref_types
        self.refcmds = dict([
            (refcmd, refspec)
            for ref_type in ref_types
            for refcmd, refspec in _REFCMDS[ref_type].items()
        ])

        self.use_hash_length = use_hash_length


        self.renamed_labels = {} # oldname: newname
        

        self.add_stage(self.CollectLabels(self))
        self.add_stage(self.ReplaceRefs(self))



    def specs(self, **kwargs):
        all_macros = [
                MacroSpec(mname, args_parser=MacroStandardArgsParser('{'))
                for mname in self.labelcmds
            ] + [refspec['macro'] for refspec in self.refcmds.values()]
        #all_macros = list(all_macros); logger.debug("Macros = %r", all_macros)
        return dict(macros=all_macros)


    class CollectLabels(BaseMultiStageFix.Stage):
        def __init__(self, parent_fix, **kwargs):
            super().__init__(parent_fix, **kwargs)
            self.collected_labels = []

        def fix_node(self, n, **kwargs):
            pf = self.parent_fix
            if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname in pf.labelcmds:
                if n.nodeargd is not None and len(n.nodeargd.argnlist) >= 1:
                    # collect argument as a label
                    labelname = self.preprocess_arg_latex(n, 0)
                    if labelname in self.collected_labels:
                        logger.warning("Duplicate label encountered ‘%s’", labelname)
                    else:
                        self.collected_labels.append( labelname )

        def stage_finish(self):
            # rename all labels
            pf = self.parent_fix
            pf.compute_renamed_labels(self.collected_labels)

    class ReplaceRefs(BaseMultiStageFix.Stage):
        def __init__(self, parent_fix, **kwargs):
            super().__init__(parent_fix, **kwargs)
            self.collected_labels = []

        def arg_to_latex(self, n):
            if n.isNodeType(latexwalker.LatexGroupNode):
                return ''.join(nn.to_latex() for nn in n.nodelist
                               if not nn.isNodeType(latexwalker.LatexCommentNode))
            return n.to_latex()


        def replace_node_args(self, n, label_args):
            pf = self.parent_fix
            if n.nodeargd is None or max(label_args) >= len(n.nodeargd.argnlist):
                return

            for arg_i in label_args:
                n_arg = n.nodeargd.argnlist[arg_i]
                lblargs = [x.strip()
                           for x in self.arg_to_latex(n_arg).split(',')
                           if x.strip()]
                newlblarg = ",".join([
                    pf.renamed_labels.get(l, l)
                    for l in lblargs
                ])
                n.nodeargd.argnlist[arg_i] = n.parsing_state.lpp_latex_walker.make_node(
                    latexwalker.LatexGroupNode,
                    nodelist=[n.parsing_state.lpp_latex_walker.make_node(
                        latexwalker.LatexCharsNode,
                        chars=newlblarg,
                        parsing_state=n.parsing_state,
                        pos=None, len=None,
                    )],
                    delimiters=('{','}'),
                    parsing_state=n.parsing_state,
                    pos=None, len=None
                )

        def fix_node(self, n, **kwargs):
            pf = self.parent_fix
            if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname in pf.refcmds:
                refname = n.macroname
                label_args = pf.refcmds[refname]['label_args']
                self.preprocess_child_nodes(n)
                self.replace_node_args(n, label_args)
            if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname in pf.labelcmds:
                self.preprocess_child_nodes(n)
                self.replace_node_args(n, [0])



    def compute_renamed_labels(self, collected_labels):
            
        def _get_prefix(j, labelname):
            j = labelname.find(':')
            if j > 0:
                return labelname[:j+1]
            return ''
        d = {
            'num_labels': len(collected_labels),
            'hash': lambda j, labelname: \
                hashlib.md5(labelname.encode('utf-8')).hexdigest()[:self.use_hash_length],
            'n': lambda j, labelname: j,
            'prefix': _get_prefix
        }

        for j, l in enumerate(collected_labels):

            newl = self.label_rename_fmt % _WrapContext(d, [j, l], {})

            dupl_counter = None
            while newl in self.renamed_labels.values():
                # duplicate!!
                if dupl_counter is None:
                    newl += ".1"
                    dupl_counter = 1
                else:
                    dupl_counter += 1
                    newl = newl[:newl.rfind('.')] + str(dupl_counter)

            self.renamed_labels[l] = newl


class _WrapContext:
    def __init__(self, d, args, kwargs):
        self.d = d
        self.args = args
        self.kwargs = kwargs
    def __contains__(self, key):
        return key in self.d
    def __getitem__(self, key):
        value = self.d[key]
        if callable(value):
            return value(*self.args, **self.kwargs)
        return value
