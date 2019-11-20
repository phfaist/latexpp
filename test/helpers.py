import os
import os.path

import json
import logging
import unittest

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

        outdata = self.execute_string(s, input_source='"file" {} [if you know what I mean]'.format(fname))

        self.register_output_file(output_fname)

        # "write" to the given file
        self.wrote_executed_files[output_fname] = outdata


    def _os_walk_output_dir(self):
        return [('/TESTOUT', [], [d for s, d in self.copied_files])]

    def _do_ensure_destdir(self, destdir, destdn):
        pass

    def _do_copy_file(self, source, dest):
        self.copied_files.append( (source, dest,) )


    def check_autofile_up_to_date(self, autotexfile):
        # skip checks
        return




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



class LatexWalkerNodesComparer:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assert_nodelists_equal(self, nodelist, d, *, line_numbers=True):

        from pylatexenc.latexwalker import make_json_encoder

        lw = next(n.parsing_state.lpp_latex_walker
                  for n in nodelist
                  if n is not None,
                  None)

        if lw is not None:
            json_cls = make_json_encoder(latexwalker, use_line_numbers=line_numbers)
        else:
            json_cls = None

        # make (json-serializable) data tree from nodelist in the same way as we make the JSON object
        newd = json.load(
            json.dumps(nodelist, cls=json_cls)
        )

        self.assertEqual(newd, d)



def test_main():
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
