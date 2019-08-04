
import logging
import unittest

from latexpp import preprocessor 

class MockLPP(preprocessor.LatexPreprocessor):
    def __init__(self):
        super().__init__(
            output_dir='TESTOUT',
            main_doc_fname='TESTDOC',
            main_doc_output_fname='TESTMAIN'
        )
        self.copied_files = []
        self.output_dir = '/TESTOUT' # simulate output here

    def execute(self, latex):
        self.initialize()
        s = self.execute_string(latex, input_source='[test string]')
        self.finalize()
        return s

    def _os_walk_output_dir(self):
        return [('/TESTOUT', [], [d for s, d in self.copied_files])]

    def _do_copy_file(self, source, dest):
        self.copied_files.append( (source, dest,) )


    def check_autofile_up_to_date(self, autotexfile):
        # skip checks
        return



def test_main():
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
