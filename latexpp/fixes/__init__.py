

class BaseFix:
    #
    # Promise: BaseFix does not have an __init__().  Subclasses are not required
    # to call the super's __init__().
    #

    def initialize(self, lpp):
        pass

    def fix_node(self, n, lpp):
        pass

    def finalize(self, lpp):
        pass
