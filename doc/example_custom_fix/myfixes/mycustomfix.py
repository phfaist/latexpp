import logging
logger = logging.getLogger(__name__) # log messages

from pylatexenc.macrospec import MacroSpec, EnvironmentSpec
from pylatexenc import latexwalker

from latexpp.fix import BaseFix

class MyGreetingFix(BaseFix):
    r"""
    The documentation for my custom fix goes here.
    """

    def __init__(self, greeting='Hi there, %(name)s!'):
        self.greeting = greeting
        super().__init__()

    def specs(self, **kwargs):
        return dict(macros=[
            # tell the parser that \greet is a macro that takes a
            # single mandatory argument
            MacroSpec("greet", "{")
        ])

    def fix_node(self, n, **kwargs):

        if (n.isNodeType(latexwalker.LatexMacroNode) 
            and n.macroname == 'greet'):

            # \greet{Someone} encountered in the document

            # Even if we declared the \greet macro to accept an
            # argument, it might happen in some cases that n.nodeargd
            # is None or has no arguments.  This happens, e.g. for
            # ``\newcommand{\greet}...``.  In such cases, leave this
            # \greet unchanged:
            if n.nodeargd is None or not n.nodeargd.argnlist:
                return None # no change

            # make sure arguments are preprocessed, too, and
            # then get the argument as LaTeX code:
            arg = self.preprocess_contents_latex(n.nodeargd.argnlist[0])
            
            # return the new LaTeX code to put in place of the entire
            # \greet{XXX} invocation.  Here, we use the string stored
            # in self.greeting.  We assume that that string has a
            # '%(name)s' in it that can replace with the name of the
            # person to greet (the macro argument that we just got).
            # We use the % operator in python for this cause it's
            # handy.

            # use logger.debug(), logger.info(), logger.warning(),
            # logger.error() to print out messages, debug() will be
            # visible if latexpp is called with --verbose
            logger.debug("Creating greeting for %s", arg)

            # don't forget to use raw strings r'...' for latex code,
            # to avoid having to escape all the \'s
            return r'\emph{' + self.greeting % {"name": arg} + '}'

        return None
