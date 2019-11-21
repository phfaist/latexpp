import os
import os.path

import logging
import fileinput
import json

from pylatexenc import latexwalker

from helpers import nodelist_to_d


if __name__ == '__main__':
    
    in_latex = ''
    for line in fileinput.input():
        in_latex += line

    nodelist = latexwalker.LatexWalker(in_latex, tolerant_parsing=False).get_latex_nodes()[0]

    d = nodelist_to_d(nodelist)

    print(repr(d))

    print(json.dumps(d, indent=4))
