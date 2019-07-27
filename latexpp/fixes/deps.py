import re
import os
import os.path
import logging

logger = logging.getLogger(__name__)


class CopyFilesFixes(object):
    def __init__(self, files=[]):
        self.files = files

    def initialize(self, lpp, **kwargs):

        for fn in self.files:
            lpp.copy_file(fn)


    def fix_node(self, n, lpp):
        return None
