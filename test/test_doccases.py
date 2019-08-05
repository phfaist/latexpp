
import unittest

import os.path
import tempfile
import shutil
import logging
import filecmp

from latexpp import __main__ as mainmodule

# prevent main module from setting up its own logging handlers etc.
mainmodule.setup_logging = lambda *args, **kwargs: None

import helpers


#
# TO DEBUG: Create an empty subdir in this directory called '_tmpdir' and set
# `use_mkdtemp=False` below.  The processed bibolamazi file will be left there,
# we can diff with the original to see what happened.  Don't forget to clean up
# the directory for each run.
#
use_mkdtemp = True #False
localtmpdir = '_tmpdir' # used if use_mkdtemp=False


test_cases_dir = os.path.join(os.path.realpath(os.path.dirname(os.path.abspath(__file__))), 
                              'doccases')


class DocCaseTester:
    def __init__(self):
        super().__init__()

    def _run_doc_case_test(self, casename):

        logging.getLogger(__name__).info(
            "********** RUNNING DOC CASE TEST %s **********",
            casename
        )
        
        if use_mkdtemp:
            tmpdir = tempfile.mkdtemp()
        else:
            tmpdir = os.path.abspath(os.path.join(os.path.dirname(__file__), localtmpdir))

        try:
            
            shutil.copytree(os.path.join(test_cases_dir, casename),
                            os.path.join(tmpdir, casename),
                            ignore=shutil.ignore_patterns('_latexpp_output'))

            # run _latexpp_output
            
            cwd = os.getcwd()
            try:
                os.chdir(os.path.join(tmpdir, casename))
                mainmodule.main([])
            finally:
                os.chdir(cwd)
                
            # compare directories to see if there are any changes
            dcmp = filecmp.dircmp(
                os.path.join(test_cases_dir, casename, '_latexpp_output'),
                os.path.join(tmpdir, casename, '_latexpp_output')
            )

            dcmp.report_full_closure()

            self.assert_dcmp_nodiffs(dcmp)

        finally:
            if use_mkdtemp:
                shutil.rmtree(tmpdir)

    def assert_dcmp_nodiffs(self, dcmp):
        self.assertEqual(len(dcmp.left_only), 0)
        self.assertEqual(len(dcmp.right_only), 0)
        self.assertEqual(len(dcmp.diff_files), 0)
        self.assertEqual(len(dcmp.funny_files), 0)
        for sd in dcmp.subdirs.values():
            self.assert_dcmp_nodiffs(dcmp)


class TestDocCases(unittest.TestCase, DocCaseTester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.maxDiff = None

    def test_case01(self):
        self._run_doc_case_test('case01')



if __name__ == '__main__':
    helpers.test_main()
