r"""
Module that provides the base class for a *latexpp* fix.
"""

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

    See :ref:`customfix` for a tutorial and reference on writing a custom fix
    class.

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
    """
    def __init__(self):
        self.lpp = None
        self._basefix_constr_called = True # preprocessor checks this to prevent silly bugs

    def fix_name(self):
        return self.__class__.__module__ + '.' + self.__class__.__name__

    def set_lpp(self, lpp):
        self.lpp = lpp


    def initialize(self):
        pass

    def specs(self):
        r"""
        Return any custom macro, environment and specials specifications that might
        be needed for the latex walker's context.

        Return `None` if no definitions are needed, or return a dict with keys
        'macros', 'environments', and 'specials' with lists of corresponding
        definitions.  The return value of `specs()` should be suitable for use
        as keyword arguments to
        `macrospec.LatexContextDb.add_context_category()`.
        """
        return None

    def finalize(self):
        pass


    def add_preamble(self):
        return None


    def preprocess(self, nodelist):
        r"""
        Return a new node list that corresponds to the pre-processed version of
        `nodelist`.

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
            return self._parse_nodes(newnodelist, parsing_state=ps)
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
                # make sure child nodes are preprocessed.
                self.preprocess_child_nodes(n)
                newnodelist.append(n)
                continue

            if isinstance(nn, str):
                # if it is a str then we need to re-parse output into nodes
                nn = self._parse_nodes(nn, parsing_state=n.parsing_state)
                # fall through case is list ->
            if isinstance(nn, list):
                # preprocess new replacement node list
                newnodelist.extend(nn)
                continue

            newnodelist.append(nn)

        return newnodelist


    def preprocess_child_nodes(self, node):
        r"""
        Call `self.preprocess()` on all children of the given node `node` and
        modifies the node attributes in place.

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


    def _parse_nodes(self, s, parsing_state):
        # returns a node list
        try:
            lw = self.lpp.make_latex_walker(s)
            nodes, _, _ = lw.get_latex_nodes(
                parsing_state=lw.make_parsing_state(**parsing_state.get_fields())
            )
            return nodes
        except latexwalker.LatexWalkerParseError as e:
            logger.error("Internal error: can't re-parse preprocessed latex:\n%r\n%s",
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

        if newnode.isNodeType(latexwalker.LatexGroupNode):
            newnode.nodelist = self.preprocess(newnode.nodelist)
            return newnode

        if isinstance(newnode, str):
            newnode = self._parse_nodes(newnode, node.parsing_state) # re-parse with latexwalker etc.
            # fall through to list case ->

        if isinstance(newnode, list):
            nx = newnode
            # run arguments also through our preprocessor:
            nx = self.preprocess(nx)
            return node.parsing_state.lpp_latex_walker.make_node(
                latexwalker.LatexGroupNode,
                nodelist=nx,
                delimiters=('{', '}'),
                parsing_state=node.parsing_state,
            )
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
          in any way.  (In this case, this method does not need to inspect child
          nodes, as they will be visited separately.)

        - return a string: The string is parsed into a node list, and the
          resulting nodes are used as a replacement of the original `node`.

        - return a node instance or a node list: The node(s) are used in the
          place of the original `node`.

        If this method returns a valid replacement for the given `node`, i.e.,
        anything that is not `None`, then *this method is responsible for
        recursing into child nodes*.  This can be done by using the methods
        :py:meth:`preprocess()`, :py:meth:`preprocess_child_nodes()`,
        :py:meth:`preprocess_latex()`, and
        :py:meth:`preprocess_contents_latex()` on the nodes that

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
        return self.lpp.nodelist_to_latex(n2)

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
