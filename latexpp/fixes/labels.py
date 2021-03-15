#import re
#import itertools
import hashlib
import base64
import logging

logger = logging.getLogger(__name__)

from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser
from pylatexenc import latexwalker

from latexpp.fix import BaseMultiStageFix

from . import ref as lppfix_ref


_REFCMDS = dict(lppfix_ref._REFCMDS)
_REFCMDS_ref_types = lppfix_ref._REFCMDS_ref_types

_LABELCMDS = {
    'ref': {
        'label': {'macro': MacroSpec('label', args_parser=MacroStandardArgsParser('{')),
                  'label_args': [0]},
    },
    'bib': {
        'bibitem': {'macro': MacroSpec('bibitem', args_parser=MacroStandardArgsParser('[{')),
                    'label_args': [1]},
    },
}



class RenameLabels(BaseMultiStageFix):
    r"""
    Detect labels pinned with \label{} and replace all future references in
    known referencing commands.

    Arguments:
    
      - `label_rename_fmt`: a python %-format string to generate the new label.
        Use fields of the type ``"%(prefix)s%(hash)s"`` or ``%(n)d``.  Keys can
        include:

        - ``labelname`` (earlier label name);

        - ``n`` (a simple incremental counter for each label);

        - ``hash`` (a hash of the earlier label);
    
        - ``prefix`` (detects the prefix like "thm:" or "eq:", including colon;
          expands to empty if no prefix);

        - ``num_labels`` (total number of detected labels).

        - [I will probably add more fields in the future.]

      - `ref_types`: which reference command types to recognize when replacing
        labels.  Here we use the same syntax as the
        :py:class:`latexpp.fixes.ref.ExpandRefs` filter.

        Additionally, you can specify the 'bib' "reference type" to act on
        bibliographic entries; labels will be searched for (and replaced) in
        ``\bibitem{}`` commands and replacements will occur in citation-related
        commands like ``\cite{}``, ``\citet{}``, etc.  By default, bibliographic
        labels are not touched.

      - `use_hash_length`: The key "%(hash)s" in `label_rename_fmt` computes the
        MD5 hash of the previous label and truncates its encoded representation
        (see `use_hash_encoding`) at `use_hash_length` chars.

      - `use_hash_encoding`: one of 'hex' (hexadecimal) or 'b64' (base64 with
        '-' and '.' chars instead of '+' and '/')
    """
    def __init__(self, *,
                 label_rename_fmt='%(prefix)s%(hash)s',
                 ref_types=None,
                 use_hash_length=12,
                 use_hash_encoding='b64',
                 hack_phfthm_proofs=False):

        super().__init__()

        self.label_rename_fmt = label_rename_fmt

        if ref_types is None:
            ref_types = list(_REFCMDS_ref_types)

        self.ref_types = ref_types
        self.refcmds = dict([
            (refcmd, refspec)
            for ref_type in ref_types
            for refcmd, refspec in _REFCMDS[ref_type].items()
        ])
        label_ref_types = set()
        for r in ref_types:
            if r in _REFCMDS_ref_types:
                # standard ref-type
                label_ref_types |= set(['ref'])
                continue
            label_ref_types |= set([r])
        self.labelcmds = dict([
            (labelcmd, labelspec)
            for label_ref_type in label_ref_types
            for labelcmd, labelspec in _LABELCMDS[label_ref_type].items()
        ])

        self.use_hash_length = use_hash_length
        self.use_hash_encoding = use_hash_encoding

        self.hack_phfthm_proofs = hack_phfthm_proofs

        self.renamed_labels = {} # oldname: newname
        
        self.add_stage(self.CollectLabels(self))
        self.add_stage(self.ReplaceRefs(self))


    def specs(self, **kwargs):
        all_macros = [
            labelspec['macro']
            for labelspec in self.labelcmds.values()
        ] + [
            refspec['macro']
            for refspec in self.refcmds.values()
        ]
        #all_macros = list(all_macros); logger.debug("Macros = %r", all_macros)
        return dict(macros=all_macros)


    class CollectLabels(BaseMultiStageFix.Stage):
        def __init__(self, parent_fix, **kwargs):
            super().__init__(parent_fix, **kwargs)
            self.collected_labels = []

        def fix_node(self, n, **kwargs):
            pf = self.parent_fix
            if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname in pf.labelcmds:
                labelname = n.macroname
                label_args = pf.labelcmds[labelname]['label_args']

                for lblarg in label_args:
                    if n.nodeargd is not None and len(n.nodeargd.argnlist) >= lblarg:
                        # collect argument as a label
                        labelname = self.preprocess_arg_latex(n, lblarg)
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


        def replace_node_args(self, n, label_args, *, preserve_prefixes=None):
            pf = self.parent_fix
            if n.nodeargd is None or max(label_args) >= len(n.nodeargd.argnlist):
                return

            if not preserve_prefixes:
                preserve_prefixes = []

            def get_new_label(l):
                for p in preserve_prefixes:
                    if l.startswith(p):
                        l = l[len(p):]
                        return p + pf.renamed_labels.get(l, l)
                return pf.renamed_labels.get(l, l)

            for arg_i in label_args:
                n_arg = n.nodeargd.argnlist[arg_i]
                lblargs = [x.strip()
                           for x in self.arg_to_latex(n_arg).split(',')
                           if x.strip()]
                newlblarg = ",".join([
                    get_new_label(l)
                    for l in lblargs
                ])
                delims = ('{', '}')
                if n.nodeargd.argnlist[arg_i].isNodeType(latexwalker.LatexGroupNode):
                    # use same "group" delimiters as before
                    delims = n.nodeargd.argnlist[arg_i].delimiters
                n.nodeargd.argnlist[arg_i] = n.parsing_state.lpp_latex_walker.make_node(
                    latexwalker.LatexGroupNode,
                    nodelist=[n.parsing_state.lpp_latex_walker.make_node(
                        latexwalker.LatexCharsNode,
                        chars=newlblarg,
                        parsing_state=n.parsing_state,
                        pos=None, len=None,
                    )],
                    delimiters=delims,
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
                labelname = n.macroname
                label_args = pf.labelcmds[labelname]['label_args']
                self.preprocess_child_nodes(n)
                self.replace_node_args(n, label_args)

            if pf.hack_phfthm_proofs and n.isNodeType(latexwalker.LatexEnvironmentNode) \
               and n.environmentname == 'proof':
                self.preprocess_child_nodes(n)
                self.replace_node_args(n, [0], preserve_prefixes=('**','*',))



    def compute_renamed_labels(self, collected_labels):
            
        def _get_prefix(j, labelname):
            j = labelname.find(':')
            if j > 0:
                return labelname[:j+1]
            return ''
        def _get_hash(j, labelname):
            m = hashlib.md5(labelname.encode('utf-8'))
            hashstr = None
            if self.use_hash_encoding == 'hex':
                hashstr = m.hexdigest()
            elif self.use_hash_encoding == 'b64':
                digest = m.digest()
                hashstr = base64.urlsafe_b64encode(digest).decode('utf-8')
                hashstr = hashstr.replace('_', '.')
            else:
                raise ValueError("Invalid use_hash_encoding=%s"%(self.use_hash_encoding))
            return hashstr[:self.use_hash_length]
        d = {
            'num_labels': len(collected_labels),
            'labelname': lambda j, labelname: labelname,
            'hash': _get_hash,                
            'n': lambda j, labelname: j,
            'prefix': _get_prefix,
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
