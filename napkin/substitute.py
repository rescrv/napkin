from lib2to3 import fixer_base
from lib2to3 import fixer_util

class FixSubstitute(fixer_base.BaseFix):
    PATTERN = "expr_stmt< NAME '=' any * >"

    def transform(self, node, results):
        if len(node.children) < 3: return node
        if node.children[0].value != node.children[0].value.upper(): return node
        tool = self.options['NAPKIN']
        options, prefix = tool.interpret_comment(node.next_sibling.prefix)
        node.next_sibling.prefix = prefix
        replace = tool.substitute(node.children[0].value, options)
        if replace is not None:
            node.children = node.children[:2]
            node.children.append(fixer_util.String(' ' + replace))
        return node
