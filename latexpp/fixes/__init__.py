
from pylatexenc import latexwalker

class BaseFix:
    r"""
    Base class for defining specific `latexpp` fixes.

    A `fix` should be defined by defining a subclass of this class and
    overriding the methods that will allow to transform nodes.

    See :ref:`customfix` for an introduction to writing a custom fix class.

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
        `nodelist`.  It's the `BaseFix`\ 's responsibility to recurse into
        subnodes.

        Don't subclass this, rather, you should subclass
        :py:meth:`fix_nodelist()` or :py:meth:`fix_node()`.
        """

        newnodelist = self._call_fix_nodelist(nodelist)

        # recurse into subnodes

        for n in newnodelist:

            if n.isNodeType(latexwalker.LatexGroupNode):
                n.nodelist = self._call_fix_nodelist(n.nodelist)

            if n.isNodeType(latexwalker.LatexMacroNode):
                if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                    for j in range(len(n.nodeargd.argnlist)):
                        n.nodeargd.argnlist[j] = self._call_fix_argnode(n.nodeargd.argnlist[j])

            if n.isNodeType(latexwalker.LatexEnvironmentNode):
                if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                    for j in range(len(n.nodeargd.argnlist)):
                        #print("Before arg node: ", n.nodeargd.argnlist[j])
                        n.nodeargd.argnlist[j] = self._call_fix_argnode(n.nodeargd.argnlist[j])
                        #print("New arg node: ", n.nodeargd.argnlist[j])

                n.nodelist = self._call_fix_nodelist(n.nodelist)

            if n.isNodeType(latexwalker.LatexSpecialsNode):
                if n.nodeargd is not None and n.nodeargd.argnlist is not None:
                    for j in range(len(n.nodeargd.argnlist)):
                        n.nodeargd.argnlist[j] = self._call_fix_argnode(n.nodeargd.argnlist[j])

            if n.isNodeType(latexwalker.LatexMathNode):
                n.nodelist = self._call_fix_nodelist(n.nodelist)

        return newnodelist

    def _parse_nodes(self, s):
        # returns a node list
        try:
            lw = self.lpp.make_latex_walker(s)
            return lw.get_latex_nodes()[0]
        except latexwalker.LatexWalkerParseError as e:
            logger.error("Internal error: can't re-parse preprocessed latex:\n%r\n%s",
                         s, e)
            raise

    def _call_fix_nodelist(self, nodelist):
        # first call fix_nodelist()
        newnodelist = self.fix_nodelist(nodelist)
        if newnodelist is None:
            newnodelist = nodelist
        if isinstance(newnodelist, str):
            newnodelist = self._parse_nodes(newnodelist) # re-parse with latexwalker etc.
        return newnodelist

    def _call_fix_argnode(self, node):
        if node is None:
            return None
        if node.isNodeType(latexwalker.LatexGroupNode):
            node.nodelist = self._call_fix_nodelist(node.nodelist)
            return node
        newnode = self.fix_node(node, is_single_token_arg=True)
        if newnode is None:
            return node
        if isinstance(newnode, str):
            newnode = self._parse_nodes(newnode) # re-parse with latexwalker etc.
        if isinstance(newnode, list):
            nx = newnode
            thelatex = ''.join(n.latex_verbatim() for n in nx)
            return latexwalker.LatexGroupNode(
                nodelist=newnode,
                delimiters=('{', '}'),
                parsed_context=latexwalker.ParsedContext(
                    s=thelatex,
                    latex_context=node.parsed_context.latex_context
                ),
                pos=0,
                len=len(thelatex)
            )
        return newnode



    def fix_nodelist(self, nodelist):
        r"""
        This method is one of two methods responsible for implementing the node
        transformations for this fix class.

        This method should not modify `nodelist` itself, rather, it should
        return a representation of the transformed node list.

        This method should return `None`, a node list, or a string.  A `None`
        return value signals that no transformation is necessary.  If a node
        list is returned, it is used as the transformed list.  If a string is
        returned, it is parsed into a node list again and that node list is
        used.

        In most cases, you should only override :py:meth:`fix_node()`.  In
        advanced cases where you need to act on the whole list globally (perhaps
        to detect specific sequences of nodes, etc.), then you need to
        reimplement :py:meth:`fix_nodelist()`.
        
        By default, :py:meth:`fix_nodelist()` calls :py:meth:`fix_node()` for
        each node of the nodelist and concatenates the results into a new node
        list.  If you reimplement :py:meth:`fix_nodelist()`, make sure you call
        the base implementation or you need to worry yourself about calling
        :py:meth`fix_node()`.

        There is (currently) exactly one situation where :py:meth:`fix_node()`
        will is not called from :py:meth:`fix_nodelist()`.  This is when a
        single token is found as a macro/environment/specials argument without
        the token being wrapped in a LaTeX group.
        """
        newnodelist = []
        for n in nodelist:
            # call fix_node()
            nn = self.fix_node(n, prev_node=(newnodelist[-1] if len(newnodelist) else None))
            if nn is None:
                newnodelist.append(n)
                continue
            if isinstance(nn, str):
                # need to re-parse
                newnodelist.extend(self._parse_nodes(nn))
                continue
            if isinstance(nn, list):
                newnodelist.extend(nn)
                continue
            newnodelist.append(nn)

        return newnodelist


    def fix_node(self, node, *, is_single_token_arg=False, prev_node=None):
        r"""
        Transforms a given node to implement the fixes provided by this fix class.

        In most cases, your fix class only needs to reimplement
        :py:meth:`fix_node()`.

        Subclasses should inspect `node` and return one of either:

        - return `None`: If the node does not need to be transformed in any way.
          In any case, child nodes will be visited and fixed by other calls to
          :py:meth:`fix_node()`.

        - return a string: The string is parsed into a node list, and the
          resulting nodes are used as a replacement of the original `node`.

        - return a node instance or a node list: The node(s) are used in the
          place of the original `node`.

        With this method the nodes are considered one by one.  If you need to
        act globally on the full node list, you will have to override
        :py:meth:`fix_nodelist()`.

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
    def node_contents_to_latex(self, *args, **kwargs):
        return self.lpp.node_contents_to_latex(*args, **kwargs)

    def node_arglist_to_latex(self, *args, **kwargs):
        return self.lpp.node_arglist_to_latex(*args, **kwargs)
