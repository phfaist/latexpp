import re
import os.path as os_path # allow tests to monkey-patch this

import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexwalker import LatexMacroNode
#from pylatexenc.latexencode import unicode_to_latex

from latexpp.fix import BaseFix

from .labels import RenameLabels


_exts = ['', '.lplx', '.pdf', '.png', '.jpg', '.jpeg', '.eps']



class CopyAndRenameFigs(BaseFix):
    r"""
    Copy graphics files that are included by ``\includegraphics`` commands to
    the output directory.  By default, they are renamed in figure order,
    'fig-01.jpg', 'fig-02.pdf', etc.

    Arguments:

    - `fig_rename`: Template to use when renaming the graphics file in the
      output directory.  The string is parsed by python's ``str.format()``
      mechanism, and the following keys are provided:
    
        - '{fig_counter}', '{fig_counter:02}' -- the figure number.  Use ':0n'
          to format the number with `n` digits and leading zeros.

        - '{fig_ext}' -- the file name extension, including the dot.

        - '{orig_fig_name}' -- the original figure file name

        - '{orig_fig_basename}' -- the original figure file name, w/o extension

        - '{orig_fig_ext}' -- the original figure file extension

    - `start_fig_counter`: Figure numbering starts at this number (by default,
      1).
    """

    def __init__(self, fig_rename='fig-{fig_counter:02}{fig_ext}',
                 start_fig_counter=1, graphicspath=".", exts=None):
        super().__init__()

        # By default we start at Fig #1 because journals like separate files
        # with numbered figures starting at 1
        self.fig_counter = start_fig_counter
        self.fig_rename = fig_rename
        self.graphicspath = graphicspath
        self.exts = exts if exts is not None else _exts
        
        self.post_processors = {
            '.lplx': self.do_postprocess_lplx,
        }

        self.lplx_files_to_finalize = []


    def fix_node(self, n, **kwargs):

        if n.isNodeType(LatexMacroNode) and n.macroname == 'includegraphics':
            # note, argspec is '[{'

            # find file and copy it
            orig_fig_name = self.preprocess_arg_latex(n, 1)
            orig_fig_name = os_path.join(self.graphicspath, orig_fig_name)
            for e in self.exts:
                if os_path.exists(orig_fig_name+e):
                    orig_fig_name = orig_fig_name+e
                    break
            else:
                logger.warning("File not found: %s. Tried extensions %r",
                               orig_fig_name, self.exts)
                return None # keep the node as it is
            
            if '.' in orig_fig_name:
                orig_fig_basename, orig_fig_ext = orig_fig_name.rsplit('.', maxsplit=1)
                orig_fig_basename = os_path.basename(orig_fig_basename)
                orig_fig_ext = '.'+orig_fig_ext
            else:
                orig_fig_basename, orig_fig_ext = os_path.basename(orig_fig_name), ''

            figoutname = self.fig_rename.format(
                fig_counter=self.fig_counter,
                fig_ext=orig_fig_ext,
                orig_fig_name=orig_fig_name,
                orig_fig_basename=orig_fig_basename,
                orig_fig_ext=orig_fig_ext
            )

            self.lpp.copy_file(orig_fig_name, figoutname)

            if orig_fig_ext in self.post_processors:
                pp_fn = self.post_processors[orig_fig_ext]
                pp_fn(
                    node=n,
                    orig_fig_name=orig_fig_name,
                    orig_fig_basename=orig_fig_basename,
                    orig_fig_ext=orig_fig_ext,
                    figoutname=figoutname,
                )

            # increment fig counter
            self.fig_counter += 1

            # don't use unicode_to_latex(figoutname) because actually we would
            # like to keep the underscores as is, \includegraphics handles it I
            # think
            return (
                r'\includegraphics' + self.preprocess_latex(self.node_get_arg(n, 0)) + \
                '{' + figoutname + '}'
            )

        return None


    def do_postprocess_lplx(self, node, orig_fig_name, figoutname, **kwargs):

        rx_lplx_read = re.compile(
            r'\\lplxGraphic\{(?P<dep_file_basename>[^}]+)\}\{(?P<dep_file_ext>[^}]+)\}'
        )


        self.lplx_files_to_finalize.append(figoutname)

        f_contents = None
        with self.lpp.open_file(orig_fig_name, encoding='utf-8') as f:
            f_contents = f.read()

        m = rx_lplx_read.search(f_contents)
        
        if m is None:
            logger.error("Could not read dependent LPLX graphic file, your build "
                         "might be incomplete!")
            return []

        # find and copy the dependent file

        dep_basename = m.group('dep_file_basename')
        dep_basename = os_path.join(self.graphicspath, dep_basename)

        dep_ext = m.group('dep_file_ext')

        dep_name = dep_basename + dep_ext

        dep_figoutname = self.fig_rename.format(
            fig_counter=self.fig_counter,
            fig_ext=dep_ext,
            orig_fig_name=dep_name,
            orig_fig_basename=dep_basename,
            orig_fig_ext=dep_ext,
        )

        node.lpp_graphics_lplx_is_lplx_file = True
        node.lpp_graphics_lplx_output_file = figoutname
        node.lpp_graphics_lplx_dependent_output_file = dep_figoutname

        # copy to destination

        logger.debug(f"Detected LPLX dependent file {dep_name}")

        self.lpp.copy_file(dep_name, dep_figoutname)

        # patch output lplx file to find the correct dependent file

        if '.' in dep_figoutname:
            dep_figoutname_basename, dep_figoutname_mext = \
                dep_figoutname.rsplit('.', maxsplit=1)
            dep_figoutname_ext = '.'+dep_figoutname_mext
        else:
            dep_figoutname_basename, dep_figoutname_ext = dep_figoutname, ''

        patched_content = "".join([
            f_contents[:m.start()],
            r'\lplxGraphic{' + dep_figoutname_basename + '}{' + dep_figoutname_ext + '}',
            f_contents[m.end():],
        ])

        file_to_patch = os_path.join(self.lpp.output_dir, figoutname)
        with open(file_to_patch, 'w', encoding='utf-8') as fw:
            fw.write(patched_content)

        logger.debug(f"patched file {file_to_patch}")




    def finalize_lplx(self):

        # see if we have a rename-labels fix installed
        labels_fixes = []
        for fix in self.lpp.fixes:
            if isinstance(fix, RenameLabels):
                labels_fixes.append(fix)

        for labels_fix in labels_fixes:
            for lplxfigoutname in self.lplx_files_to_finalize:
                self.replace_labels_in_lplx_file(lplxfigoutname, labels_fix)


    def replace_labels_in_lplx_file(self, lplx_output_file, labels_fix):
        f_content = None
        full_output_file = os_path.join(self.lpp.output_dir,
                                        lplx_output_file)

        logger.debug(f"Patching labels in LPLX file {lplx_output_file} ...")

        with open(full_output_file, 'r', encoding='utf-8') as f:
            f_content = f.read()

        def get_new_label(lbl):
            return labels_fix.renamed_labels.get(lbl, lbl)

        # replace labels brutally, using a regex

        # rx_hr_uri = \
        #     re.compile(r'(?P<pre>\\href\{)(?P<target>[^}]+)(?P<post>\})')
        rx_hr_ref = \
            re.compile(r'(?P<pre>\\hyperref\[\{)(?P<target>[^}]+)(?P<post>\}\])')
        rx_hr_cite = \
            re.compile(r'(?P<pre>\\hyperlink\{cite.)(?P<target>[^}]+)(?P<post>\})')

        f_content = rx_hr_ref.sub(
            lambda m: "".join([m.group('pre'),
                               get_new_label(m.group('target')),
                               m.group('post')]),
            f_content
        )

        f_content = rx_hr_cite.sub(
            lambda m: "".join([m.group('pre'),
                               get_new_label(m.group('target')),
                               m.group('post')]),
            f_content
        )

        with open(full_output_file, 'w', encoding='utf-8') as fw:
            fw.write(f_content)




    def finalize(self):
        super().finalize()
        self.finalize_lplx()
