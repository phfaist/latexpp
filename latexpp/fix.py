r"""
This module provides the base class for fixes.


See :ref:`customfix` for a tutorial and reference on writing a custom fix class.
"""

import string
import logging
logger = logging.getLogger(__name__)

from pylatexenc import latexwalker



class DontFixThisNode(Exception):
    r"""
    Can be raised in :py:meth:`BaseFix.fix_node()` to indicate that the given
    node should not be "fixed".
    """
    pass


class BaseFix:
    r"""
    Base class for defining specific `latexpp` fixes.

    A `fix` should be defined by defining a subclass of this class and
    overriding the methods that will allow to transform nodes.

    The methods you should consider overriding are:

    - :py:meth:`fix_node()` — this method will be called once for each node in
      the document.  You can then "fix" the node however you like.
    
    - :py:meth:`specs()` — provide additional macro, environment and specials
      definitions to the LaTeX parser.

    - :py:meth:`initialize()` and :py:meth:`finalize()` — these will be called
      before all fixes and after all fixes have run, respectively.  You can do
      stuff here like scanning an aux file, or other tasks that need to be
      performed once only.

    - :py:meth:`add_preamble()` — include additional definitions to the preamble
      of the document.


    .. py:attribute:: lpp

       The `lpp` attribute holds a reference to the preprocessor object (a
       :py:class:`latexpp.preprocessor.LatexPreprocessor` instance).  You can
       use this to access some additional functions such as
       :py:meth:`self.lpp.copy_file()
       <latexpp.preprocessor.LatexPreprocessor.copy_file()>`.

       Note, if you create an instance of the fix manually, you need to call
       :py:meth:`set_lpp()` to set the `lpp` attribute.
    """
    def __init__(self):
        self.lpp = None
        self._basefix_constr_called = True # preprocessor checks this to prevent silly bugs
        self._fix_name = self.__class__.__module__ + '.' + self.__class__.__name__

    def fix_name(self):
        """
        Returns the full name/identifier of the fix, like
        'latexpp.fixes.ref.ExpandRefs'.  No need to reimplement this.
        """
        return self._fix_name

    def set_lpp(self, lpp):
        """
        Set the :py:attr:`lpp` attribute to `lpp`.  If you create a fix instance you
        should call this so that the fix can call utility methods on the
        preprocessor object.
        
        You don't have to call `set_lpp()` on fixes that are loaded via the
        preprocessor's :py:meth:`install_fix()
        <latexpp.preprocessor.LatexPreprocessor.install_fix()>` method.
        """
        self.lpp = lpp


    def initialize(self):
        """
        This method is called at the beginning, after having parsed the document,
        but before any other fixes actually process the document.

        This is a good opportunity to parse an AUX file, to create a
        sub-preprocessor, or perform some other task that needs to be done once
        before applying transformations throughout the document.

        The default implementation does nothing, reimplement to do something
        useful for your fix.
        """
        pass

    def specs(self):
        r"""
        Return any custom macro, environment and specials specifications that might
        be needed for the latex walker's context.

        Return `None` if no definitions are needed, or return a dict with keys
        'macros', 'environments', and 'specials' with lists of corresponding
        definitions.  The return value of `specs()` should be suitable for use
        as keyword arguments to
        :py:meth:`pylatexenc.macrospec.LatexContextDb.add_context_category()`.

        Specify a :py:class:`pylatexenc.macrospec.MacroSpec` for each macro you
        want to define.  The second argument is a string that describes what
        arguments the macro expects.  Each character in the string may be '*',
        '[' or '{' indicating an optional star ('*'), an optional argument
        delimited by square brackets, or a mandatory argument (single token or
        braced group).  The arguments are stored in the `node.nodeargd.argnlist`
        array in the parsed `node` (see
        :py:class:`pylatexenc.latexwalker.LatexMacroNode`) with their order
        being exactly the one given in the argument specification string where a
        value `None` indicates that an optional star or optional argument was
        not specified.

        See :py:class:`pylatexenc.macrospec.MacroSpec`,
        :py:class:`pylatexenc.macrospec.EnvironmentSpec`, and
        :py:class:`pylatexenc.macrospec.SpecialsSpec` for more detailed
        information on specifying macro, environment, and "latex specials"
        argument signatures.

        The default implementation returns `None`.  Reimplement this method to
        provide additional macro/environment/latex-specials for the parser's
        consideration.
        """
        return None

    def finalize(self):
        """
        Method that is called after all fixes have finished processing their
        transformations ("fixes").  This might be a good time to do any
        finish-up work, generate a log file with a report, or whatever one-off
        task you have to do at the end of your processing.

        The default implementation does nothing, reimplement to do something
        useful for your fix.
        """
        pass


    def add_preamble(self):
        """
        Fixes can add arbitrary code to the LaTeX preamble by subclassing this
        method and returning the required preamble definitions as a string.  The
        default implementation returns `None`, which means that no additional
        preamble definitions are requested.

        Currently, the preamble definitions are included from the start, before
        running all the fixes and they are processed as part of the document
        with all the relevant fixes.  [Don't count on this behavior, it doesn't
        sound very logical to me in hindsight, so I might change it in the
        future.]
        """
        return None


    def preprocess(self, nodelist):
        r"""
        Process the `nodelist` and apply all relevant transformations that this fix
        is meant to carry out.  Return a new node list that corresponds to the
        transformed version of `nodelist`.

        This function is what someone should call to get a full processed
        version of `nodelist`.  This method takes care of descending into child
        nodes and applying the fixes recursively by calling `preprocess()` on
        children nodes.

        Don't subclass this, rather, you should subclass
        :py:meth:`fix_nodelist()` or :py:meth:`fix_node()`.
        """

        newnodelist = self.fix_nodelist(nodelist)

        # Only continue preprocessing children nodes if fix_nodelist() returned
        # `None`.  The rule is that if fix_node() or fix_nodelist() return
        # something non-None, they are responsible for calling
        # preprocess_latex() or preprocess_children() on all child nodes.
        if isinstance(newnodelist, list):
            return newnodelist
        if isinstance(newnodelist, str):
            # re-parse with latexwalker
            ps = None
            if nodelist:
                ps = nodelist[0].parsing_state
            return self.parse_nodes(newnodelist, parsing_state=ps)
        if newnodelist is not None:
            raise ValueError("{}.fix_nodelist() did not return a string or node list"
                             .format(self.fix_name()))

        # Continue processing with fix_node()
        newnodelist = []
        for j, n in enumerate(nodelist):

            if n is None:
                continue

            # call fix_node()
            try:
                nn = self.fix_node(
                    n,
                    # newnodelist here (already preprocessed)
                    prev_node=(newnodelist[-1] if len(newnodelist) else None),
                    # nodelist here (not yet preprocessed)
                    next_node=(nodelist[j+1] if j+1<len(nodelist) else None)
                )
            except DontFixThisNode:
                nn = None
            if nn is None:
                # keep this node as it is; make sure child nodes are
                # preprocessed.
                self.preprocess_child_nodes(n)
                newnodelist.append(n)
                continue

            if isinstance(nn, str):
                # if it is a str then we need to re-parse output into nodes
                nn = self.parse_nodes(nn, parsing_state=n.parsing_state)
                # fall through case is list ->
            if isinstance(nn, list):
                # add new nodes
                newnodelist.extend(nn)
                continue

            newnodelist.append(nn)

        # make sure in the newnodelist that macro nodes are always protected by
        # a post-space, e.g., avoid a situation where a macro replacement \a ->
        # \b removed the post-space and glues the macro invokation to a
        # subsequent string.
        for j in range(len(newnodelist)-1):
            if newnodelist[j].isNodeType(latexwalker.LatexMacroNode):
                self._ensure_macro_node_maybe_post_space(newnodelist, j)

        return newnodelist

    def _ensure_macro_node_maybe_post_space(self, newnodelist, j):
        # Assumes that newnodelist[j] is a macro node

        n = newnodelist[j]
        n2 = newnodelist[j+1]

        # The only problematic situations are if the macro name is alpha and it
        # is followed by a chars node that starts with an ASCII letter
        if n.macroname[-1:] not in string.ascii_letters:
            return
        if not n2.isNodeType(latexwalker.LatexCharsNode) \
           or n2.chars[0:1] not in string.ascii_letters:
            return

        if n.nodeargd and n.nodeargd.argnlist:
            # the macro invocation has arguments

            for j in range(len(n.nodeargd.argnlist)):
                nla = n.nodeargd.argnlist[-1-j]
                if nla is None:
                    continue
                elif nla.isNodeType(latexwalker.LatexMacroNode):
                    # last argument is bare macro.  Add macro_post_space *to the
                    # argument macro node* (if we add it to n.macro_post_space,
                    # the space will appear before the macro args)
                    if not nla.macro_post_space:
                        nla.macro_post_space = ' '
                        # all ok, done
                        return
                else:
                    # no need for any protection, there is a non-bare-macro
                    # argument at the end of the specified arguments.
                    return

        # no args (or empty arg list), so make sure the macro has post_space
        if not n.macro_post_space:
            n.macro_post_space = ' ' # nothing -> single space

        return


    def preprocess_child_nodes(self, node):
        r"""
        Call `self.preprocess()` on all children of the given node `node` and
        modifies the node attributes in place.  Children include group contents
        (if a latex group), argument nodes (if a macro, environment, or latex
        specials), etc.

        This method does not return anything interesting.
        """

        n = node

        if n.isNodeType(latexwalker.LatexGroupNode):
            n.nodelist = self.preprocess(n.nodelist)

        if n.isNodeType(latexwalker.LatexMacroNode):
            if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                for j in range(len(n.nodeargd.argnlist)):
                    n.nodeargd.argnlist[j] = \
                        self._call_preprocess_argnode(n.nodeargd.argnlist[j])

        if n.isNodeType(latexwalker.LatexEnvironmentNode):
            if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                for j in range(len(n.nodeargd.argnlist)):
                    n.nodeargd.argnlist[j] = \
                        self._call_preprocess_argnode(n.nodeargd.argnlist[j])

            n.nodelist = self.preprocess(n.nodelist)

        if n.isNodeType(latexwalker.LatexSpecialsNode):
            if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                for j in range(len(n.nodeargd.argnlist)):
                    n.nodeargd.argnlist[j] = \
                        self._call_preprocess_argnode(n.nodeargd.argnlist[j])

        if n.isNodeType(latexwalker.LatexMathNode):
            n.nodelist = self.preprocess(n.nodelist)


    def parse_nodes(self, s, parsing_state):
        """
        Parses the given string `s` with an appropriate `LatexWalker` to get a node
        list again, using the given `parsing_state`.

        Returns the node list.  Raises
        :py:exc:`pylatexenc.latexwalker.LatexWalkerParseError` if there was a
        parse error.
        """
        try:
            lw = self.lpp.make_latex_walker(s)
            nodes, _, _ = lw.get_latex_nodes(
                parsing_state=lw.make_parsing_state(**parsing_state.get_fields())
            )
            return nodes
        except latexwalker.LatexWalkerParseError as e:
            logger.error("Error re-parsing intermediate latex code:\n%r\n%s",
                         s, e)
            raise

    def _call_preprocess_argnode(self, node):

        if node is None:
            return None

        try:
            newnode = self.fix_node(node, is_single_token_arg=True)
        except DontFixThisNode:
            newnode = None
        if newnode is None:
            newnode = node

        if isinstance(newnode, str):
            # re-parse with latexwalker etc.
            newnode = self.parse_nodes(newnode, node.parsing_state)
            # fall through to list case ->

        if isinstance(newnode, list):
            nx = newnode
            newnode = node.parsing_state.lpp_latex_walker.make_node(
                latexwalker.LatexGroupNode,
                nodelist=nx,
                delimiters=('{', '}'),
                parsing_state=node.parsing_state,
                pos=None, len=None
            )

        if newnode.isNodeType(latexwalker.LatexGroupNode):
            newnode.nodelist = self.preprocess(newnode.nodelist)

        return newnode


    def fix_nodelist(self, nodelist):
        r"""
        This method is one of two methods responsible for implementing the node
        transformations for this fix class.

        In most cases, you should only override :py:meth:`fix_node()`.  In
        advanced cases where you need to act on the whole list globally (perhaps
        to detect specific sequences of nodes, etc.), then you need to
        reimplement :py:meth:`fix_nodelist()`.

        You should *not* reimplement *both* :py:meth:`fix_nodelist()` and
        :py:meth:`fix_node()`.

        This method should not modify `nodelist` itself, rather, it should
        return a representation of the transformed node list.

        This method should return `None`, a node list, or a string.  A `None`
        return value signals that no transformation is to be carried out at the
        root level.  If a node list is returned, it is used as the transformed
        list.  If a string is returned, it is parsed into a node list again and
        that node list is used.

        If this method returns `None`, then we will automatically call
        :py:meth:`fix_node()` for each node of the nodelist and concatenate the
        results into a new node list.

        If this method returns a list or a string, it is also responsible for
        recursing and preprocessing all relevant child nodes in that list or
        string.  Use the methods :py:meth:`preprocess()`,
        :py:meth:`preprocess_child_nodes()`, :py:meth:`preprocess_latex()`, and
        :py:meth:`preprocess_contents_latex()` for that purpose.
        
        By default, :py:meth:`fix_nodelist()` returns `None`.
        """
        return None


    def fix_node(self, node, *, is_single_token_arg=False, prev_node=None, next_node=None):
        r"""
        Transforms a given node to implement the fixes provided by this fix class.

        In most cases, your fix class only needs to reimplement this method
        :py:meth:`fix_node()`.

        Subclasses should inspect `node` and return one of either:

        - return `None`: If the present `node` does not need to be transformed
          in any way.  (In this case, the reimplemented method does not need to
          inspect child nodes, as they will automatically be visited
          separately.)

        - return a string: The string is parsed into a node list, and the
          resulting nodes are used as a replacement of the original `node`.

        - return a node instance or a node list: The node(s) are used in the
          place of the original `node`.

        If this method returns a valid replacement for the given `node`, i.e.,
        anything that is not `None`, then *this method is responsible for
        recursing into child nodes*.  This can be done by using the methods
        :py:meth:`preprocess()`, :py:meth:`preprocess_child_nodes()`,
        :py:meth:`preprocess_latex()`, and
        :py:meth:`preprocess_contents_latex()` on the new nodes.

        If this method returns `None`, then child nodes will be preprocessed
        automatically.

        This method may raise :py:exc:`DontFixThisNode`, which has exactly the
        same effect as returning `None`.

        With this method the nodes are considered one by one.  If you need to
        act globally on the full node list, you will have to override
        :py:meth:`fix_nodelist()`.  You should not override *both*
        :py:meth:`fix_nodelist()` and :py:meth:`fix_nodes()`.

        This method gets some keyword arguments that provide some contextual
        hints:

        - If `is_single_token_arg=True`, this means that the node is in fact a
          single token used as an argument to a macro, environment or specials,
          a for the first argument in ``\newcommand\Hmax{...}``.  Such nodes
          will not have any arguments, e.g., this is not an invocation of
          ``\Hmax`` with arguments.

        - The previous node in the list of nodes that is being processed is
          provided as `prev_node` (when available).  It is `None` if the node is
          first in the list of nodes.

        .. note::
        
           Subclasses are strongly advised to accept `**kwargs` to accommodate
           future hints that might be introduced.
        """
        return None



    # utilities for subclasses
    def preprocess_latex(self, n):
        r"""
        Collects the latex representation of the given node(s) after having
        recursively preprocessed them with the present fix.

        The argument `n` may be `None`, a single node instance, or a node list.

        You may use this in your :py:meth:`fix_node()` implementations to ensure
        that preprocessing acts recursively in your replacement strings.  For
        instance::

          # transform \begin{equation*} .. \end{equation*} -> \[ .. \]
          class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
              if n.isNodeType(LatexEnvironmentNode) \
                 and n.environmentname == 'equation*':
                  # recursively apply fixes to body:
                  return r'\[' + self.preprocess_latex(n.nodelist) + r'\]'
        """
        if n is None:
            return ''
        if not isinstance(n, list):
            n = [n]
        #print("*** need to preprocess ", n)
        n2 = self.preprocess(n)
        #print("*** --> ", n2)
        return "".join(nn.to_latex() for nn in n2) #self.lpp.nodelist_to_latex(n2)

    def preprocess_contents_latex(self, n):
        r"""
        Same as :py:meth:`preprocess_latex()`, except that if `n` is a group node,
        then its contents is returned without the delimiters.  This is useful
        for expanding macro arguments, for instance::

          # transform \textbf{...} -> {\bfseries ...}
          class MyFix(fixes.BaseFix):
            def fix_node(self, n, **kwargs):
              if n.isNodeType(LatexMacroNode) and n.macroname == 'textbf':
                  # recursively apply fixes to macro argument:
                  arg_node = self.node_get_arg(n, 0)
                  return r'{\bfseries ' \
                    + self.preprocess_contents_latex(arg_node) \
                    + r'}'

        Had we used :py:func:`self.preprocess_latex()` instead, we would have
        obtained the replacement string ``{\bfseries {...}}`` with an extra pair
        of inner braces.

        Note that you can also use :py:meth:`preprocess_arg_latex()` which is
        equivalent to ``self.preprocess_contents_latex(self.node_get_arg(n,
        0))``.
        """
        if n is None:
            return ''
        if isinstance(n, list):
            return self.preprocess_latex(n)
        if n.isNodeType(latexwalker.LatexGroupNode):
            return ''.join(self.preprocess_latex(nn) for nn in n.nodelist)
        return self.preprocess_latex(n)

    def node_get_arg(self, node, argn):
        r"""
        Return the node that corresponds to the `argn`-th argument (starting at
        zero) of the given node.

        If `node` is not a macro, environment, or specials node, an error is
        raised to help detect bugs.

        If `node` does not have an argument list (`node.nodeargd is None`), then
        :py:exc:`DontFixThisNode` is raised.  This can happen if the bare macro
        is given as a single token argument e.g. to another macro.  In these
        cases you'll usually want to abort the fix; raising
        :py:exc:`DontFixThisNode` is equivalent to returning `None` in
        :py:meth:`fix_node()`.

        If `node` has an argument list (`node.nodeargd.argnlist`) that does not
        have enough arguments, then an error is raised to help detect bugs.
        """
        if not node.isNodeType(latexwalker.LatexMacroNode) and \
           not node.isNodeType(latexwalker.LatexEnvironmentNode) and \
           not node.isNodeType(latexwalker.LatexSpecialsNode):
            raise RuntimeError("internal error: node_get_arg() can only be used on "
                               "macro, environment, and specials nodes; not {!r}"
                               .format(node))
        if node.nodeargd is None or node.nodeargd.argnlist is None:
            raise DontFixThisNode

        if argn >= len(node.nodeargd.argnlist):
            # not enough arguments
            raise RuntimeError("internal error: not enough arguments for node_get_arg({}): {!r}"
                               .format(argn, node))
        
        return node.nodeargd.argnlist[argn]


    def preprocess_arg_latex(self, n, argn):
        r"""
        Same as ``self.preprocess_contents_latex(self.node_get_arg(n, argn))``.
        """
        return self.preprocess_contents_latex(self.node_get_arg(n, argn))






class BaseMultiStageFix(BaseFix):
    r"""
    Implement a fix that requires multiple passes through the document.

    On some occasions you want to implement a fix that requires multiple stages
    of processing.  For instance, the
    :py:class:`latexpp.fixes.labels.RenameLabels` fix first needs to run through
    the document to detect all ``\label{eq:xyz}`` commands, and then re-run
    through the document to replace labels in commands like ``\ref{eq:xyz}``.

    To implement a multi-stage fix, you simply inherit this class.  If you
    inherit this class *DO NOT REIMPLEMENT ANY OF THE `fix_node()`,
    `fix_nodelist()`, `preprocess()`, OR OTHER METHODS OF THAT FAMILY*.  The
    entire processing is left to the individual :py:class:`Stage` objects, which
    are themselves Fix objects that support `fix_node()`, `preprocess()`, etc.,
    which you can use normally.

    The `BaseMultiStageFix` is essentially a thin wrapper that calls each
    stage's `preprocess()` function in sequence (again, each stage is a full
    "fix" object).

    Minimal example:

    .. code-block:: python
        
        class CountMeStageFix(BaseMultiStageFix):
            def __init__(self):
                super().__init__()

                self.number_of_countmes = 0

                self.add_stage(self.CountMacros(self))
                self.add_stage(self.ReplaceMacros(self))
            
            class CountMacros(BaseMultiStageFix.Stage):
                # silly example: count number of "\countme" macros in document
                def fix_node(self, n, **kwargs):
                    if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == 'countme':
                        self.parent_fix.number_of_countmes += 1
                    return None
            
            class ReplaceMacros(BaseMultiStageFix.Stage):
                # silly example: change "\numberofcountme" macro into the actual number of
                # "\countme" macros encountered in document
                def fix_node(self, n, **kwargs):
                    if n.isNodeType(latexwalker.LatexMacroNode) \
                       and n.macroname == 'numberofcountme':
                       return str(self.parent_fix.number_of_countmes)
                    return None
    """
    def __init__(self):
        super().__init__()
        self._fix_stages = []

    class Stage(BaseFix):
        """
        A specific stage in a multi-stage fix.  A "stage" is itself a fix object
        (this class inherits :py:class:`BaseFix`) so you can reimplement the
        usual `fix_node()` or `fix_nodelist()` (see :py:class:`BaseFix`).

        .. py:attribute:: parent_fix

            You can use the attribute `self.parent_fix` to refer to the parent
            fix object (the one that inherits :py:class:`BaseMultiStageFix`) and
            access its properties when implementing your Stage object.

        You can also use the usual attributes provided by :py:class:`BaseFix`
        (for instance, you can use `self.lpp` when implementing your Stage).

        The :py:meth:`initialize()` and :py:meth:`finalize()` methods are
        honored, but the are called simultaneously for all stages before any
        stage is run and after all stages have run, respectively.  The methods
        :py:meth:`stage_start()` and :py:meth:`stage_finish()`, in contrast, are
        called immediately before and after the present stage is run.

        .. warning:: The methods `specs()` and `add_preamble()` do not work if
                     you try to implement them here. (You should implement them
                     on the parent fix instead).
        """
        def __init__(self, parent_fix):
            super().__init__()
            self.parent_fix = parent_fix

        def stage_start(self):
            """
            This method is called immediately before this stage is run, after any
            preceding stages have been run.  (In constrast, all stages'
            `initialize()` method are run before any stage is run.)
            """
            pass

        def stage_finish(self):
            """
            This method is called immediately after this stage is run, before any
            succeeding stages are run.  (In constrast, all stages' `finalize()`
            method are run after all stages are run.)
            """
            pass

        def stage_name(self):
            """
            Return a short name that describes this stage within this fix (by default,
            this is the stage's simple class name).
            """
            return self.__class__.__name__


    def add_stage(self, stage):
        if not hasattr(self, '_basefix_constr_called'):
            raise RuntimeError(
                "BaseMultiStageFix: You didn't call super().__init__() before add_stage()")

        if hasattr(self, 'lpp') and self.lpp is not None:
            stage.lpp = self.lpp
        self._fix_stages.append(stage)

    def set_lpp(self, lpp):
        for stage in self._fix_stages:
            stage.set_lpp(lpp)

    def initialize(self):
        """
        Calls all stages' `initialize()` members in stage sequence.  Don't forget to
        call the base class' implementation if you reimplement this method.

        Note that this calls the stages' initialize method at once, before any
        of the stages are actually run.  See also :py:meth:`Stage.stage_start()`
        and :py:meth:`Stage.stage_finish()`.
        """
        for stage in self._fix_stages:
            stage.initialize()

    def finalize(self):
        """
        Calls all stages' `finalize()` members in stage sequence.  Don't forget to
        call the base class' implementation if you reimplement this method.

        Note that this calls the stages' finalize method at once only after all
        the stages have finished running.  See also
        :py:meth:`Stage.stage_start()` and :py:meth:`Stage.stage_finish()`.
        """
        for stage in self._fix_stages:
            stage.finalize()

    def preprocess(self, nodelist):
        newnodelist = nodelist
        for stage in self._fix_stages:
            logger.debug("%s: running stage ‘%s’", self.fix_name(), stage.stage_name())
            stage.stage_start()
            newnodelist = stage.preprocess(newnodelist)
            stage.stage_finish()

        return newnodelist


