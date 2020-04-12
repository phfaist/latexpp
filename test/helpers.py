import os
import os.path

import logging
import unittest

from pylatexenc import latexwalker, macrospec

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



def make_latex_walker(s, **kwargs):
    return preprocessor._LPPLatexWalker(s, lpp=None, **kwargs)



class FakeOsPath:
    def __init__(self, existing_filenames):
        super().__init__()
        self.existing_filenames = existing_filenames

    def basename(self, *args, **kwargs):
        return os.path.basename(*args, **kwargs)
    def dirname(self, *args, **kwargs):
        return os.path.dirname(*args, **kwargs)

    def exists(self, fn):
        return fn in self.existing_filenames




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

        if isinstance(x, latexwalker.LatexNode):
            n = x
            d = {
                'nodetype': n.__class__.__name__
            }
            for fld in n._fields:
                d[fld] = n.__dict__[fld]

            pos = d.pop('pos', None)
            len_ = d.pop('len', None)

            if use_line_numbers:
                lineno, colno = \
                    n.parsing_state.lpp_latex_walker.pos_to_lineno_colno(n.pos)

                d['lineno'] = lineno

                if use_detailed_position:
                    d['colno'] = colno
                    d['pos'] = pos
                    d['len'] = len_

            return get_obj(d)

        if isinstance(x, macrospec.ParsedMacroArgs):
            return get_obj(x.to_json_object())

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


