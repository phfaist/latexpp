import os
import os.path

import logging
import unittest

from pylatexenc import latexwalker, macrospec

from pylatexenc.latexwalker import ParsingState

try:
    from pylatexenc.latexnodes import LatexArgumentSpec
    from pylatexenc.latexnodes.nodes import LatexNodeList
except ImportError:
    LatexArgumentSpec = type(None)
    LatexNodeList = list

from latexpp import preprocessor 


class MockLPP(preprocessor.LatexPreprocessor):
    def __init__(self, mock_files={}):
        super().__init__(
            output_dir='TESTOUT',
            main_doc_fname='TESTDOC',
            main_doc_output_fname='TESTMAIN'
        )
        self.output_dir = '/TESTOUT' # simulate output here

        self.mock_files = mock_files

        self.copied_files = []
        self.wrote_executed_files = {}

        self.omit_processed_by = True

    def _warn_if_output_dir_nonempty(self):
        pass

    def execute(self, latex):
        self.initialize()
        s = self.execute_string(latex, input_source='[test string]', omit_processed_by=True)
        self.finalize()
        return s


    def execute_file(self, fname, *, output_fname):

        s = self.mock_files[fname]

        #logging.getLogger(__name__).debug("mock execute_file(): %s -> %s, s=%r",
        #                                  fname, output_fname, s)

        outdata = self.execute_string(
            s,
            input_source='"file" {} if you know what I mean *wink wink nudge nudge*'.format(fname)
        )

        self.register_output_file(output_fname)

        # "write" to the given file
        self.wrote_executed_files[output_fname] = outdata


    def _os_walk_output_dir(self):
        return [('/TESTOUT', [], [d for s, d in self.copied_files])]

    def _do_ensure_destdir(self, destdir, destdn):
        pass

    def _do_copy_file(self, source, dest):
        source, dest = map(os.path.normpath, (source, dest))
        self.copied_files.append( (source, dest,) )

    def open_file(self, fname):
        import io
        mocklpp = self
        class X:
            def __enter__(self):
                return io.StringIO(mocklpp.mock_files[fname])
            def __exit__(self, exc_type, exc_value, exc_traceback):
                pass
                
        return X()


    def check_autofile_up_to_date(self, autotexfile):
        # skip checks
        return

    def create_subpreprocessor(self, *, lppconfig_fixes=None):
        """
        Create a sub-preprocessor (or child preprocessor) of this preprocessor.
        """
        pp = MockLPP(mock_files=self.mock_files)
        pp.parent_preprocessor = self
        if lppconfig_fixes:
            pp.install_fixes_from_config(lppconfig_fixes)
        return pp

    def finalize(self):
        if self.parent_preprocessor:
            self.parent_preprocessor.copied_files += self.copied_files
        super().finalize()



def make_latex_walker(s, **kwargs):
    return preprocessor._LPPLatexWalker(s, lpp=None, **kwargs)



class FakeOsPath:

    def __init__(self, existing_filenames):
        super().__init__()
        self.existing_filenames = [os.path.normpath(fn) for fn in existing_filenames]

    def basename(self, *args, **kwargs):
        return os.path.basename(*args, **kwargs)

    def join(self, *args, **kwargs):
        return os.path.join(*args, **kwargs)

    def dirname(self, *args, **kwargs):
        return os.path.dirname(*args, **kwargs)

    def exists(self, fn):
        return os.path.normpath(fn) in self.existing_filenames


def nodelist_to_d(nodelist, use_line_numbers=False, use_detailed_position=False):
    
    def get_obj(x):
        if x is None:
            return None

        if isinstance(x, (list, tuple)):
            return [get_obj(y) for y in x]

        if isinstance(x, dict):
            return {k: get_obj(v) for k, v in x.items()}

        if isinstance(x, (str, int, bool)):
            return x


        def _add_pos(d, pos, len_):
            if use_line_numbers:
                lineno, colno = \
                    n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(pos)

                d['lineno'] = lineno

                if use_detailed_position:
                    d['colno'] = colno
                    d['pos'] = pos
                    d['len'] = len_
            
        # we already tested for 'list', so this condition never evals to true
        # if we're running w/ pylatexenc 2
        if isinstance(x, LatexNodeList):
            d = {
                'nodelist': x.nodelist,
            }
            _add_pos(d, x.pos, x.len)
            return d

        if isinstance(x, latexwalker.LatexNode):
            n = x
            d = {
                'nodetype': n.__class__.__name__
            }
            for fld in n._fields:
                # skip some fields that we choose not to compare in our tests
                if fld in (
                        'latex_walker', 'spec', 'parsing_state',
                        'pos', 'len', 'pos_end', 
                        ):
                    continue

                d[fld] = n.__dict__[fld]

            _add_pos(d, n.pos, n.len)

            return get_obj(d)

        if isinstance(x, macrospec.ParsedMacroArgs):
            d = x.to_json_object()
            if 'arguments_spec_list' in d:
                d.pop('arguments_spec_list')
                d['argspec'] = x.argspec
            return get_obj(d)

        if isinstance(x, ParsingState):
            d = x.to_json_object()
            return get_obj(d)

        if isinstance(x, (latexwalker.LatexWalker,
                          macrospec.MacroSpec,
                          macrospec.EnvironmentSpec,
                          macrospec.SpecialsSpec,
                          LatexArgumentSpec)):
            return { '$skip-serialization-type': x.__class__.__name__ }

        raise ValueError("Unknown value to serialize: {!r}".format(x))

    return get_obj(nodelist)



class LatexWalkerNodesComparer:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assert_nodelists_equal(self, nodelist, d, **kwargs):

        newd = nodelist_to_d(nodelist, **kwargs)

        self.assertEqual(newd, d)



def test_main():
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()


