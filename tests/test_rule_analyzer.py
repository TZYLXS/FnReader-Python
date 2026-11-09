"""RuleAnalyzer（切分器）的行为测试。

用例直接对照 ``RuleAnalyzer.kt`` 的语义：分隔符只在"规则层级"生效，
选择器/谓词/引号内的分隔符必须被跳过；``%%`` 是交叉合并而不是简单拼接。
"""

import unittest

from legado_rule import RuleAnalyzer
from legado_rule.rule_analyzer import RuleAnalyzerError


class SplitRuleTest(unittest.TestCase):
    def test_simple_split(self):
        self.assertEqual(RuleAnalyzer("a&&b&&c").split_rule("&&", "||", "%%"), ["a", "b", "c"])

    def test_first_separator_wins(self):
        # 命中哪个分隔符，整条规则就只按它切
        ra = RuleAnalyzer("a&&b||c")
        self.assertEqual(ra.split_rule("&&", "||", "%%"), ["a", "b||c"])
        self.assertEqual(ra.elements_type, "&&")

    def test_brackets_protect_separator(self):
        ra = RuleAnalyzer('.book[attr="a&&b"]&&.title')
        self.assertEqual(ra.split_rule("&&", "||", "%%"), ['.book[attr="a&&b"]', '.title'])

    def test_xpath_predicate_protected(self):
        ra = RuleAnalyzer('//div[@data-x="1&&2"]&&//p/text()')
        self.assertEqual(ra.split_rule("&&"), ['//div[@data-x="1&&2"]', '//p/text()'])

    def test_quotes_protect_separator(self):
        ra = RuleAnalyzer("""a[title='x||y']||b""")
        self.assertEqual(ra.split_rule("||"), ["a[title='x||y']", "b"])

    def test_escaped_quote_inside_selector(self):
        # 引号内不处理转义（原实现如此），因此 "x\" 会提前闭合，
        # 后面的 ] 落在引号里 -> 括号层数不平衡 -> 抛错。这是"对齐缺陷"而非"修好"。
        with self.assertRaises(RuleAnalyzerError):
            RuleAnalyzer(r'a[title="x\"&&y"]&&b').split_rule("&&")

    def test_percent_is_separator(self):
        ra = RuleAnalyzer("a%%b%%c")
        self.assertEqual(ra.split_rule("&&", "||", "%%"), ["a", "b", "c"])
        self.assertEqual(ra.elements_type, "%%")

    def test_unbalanced_bracket_raises(self):
        with self.assertRaises(RuleAnalyzerError):
            RuleAnalyzer("a[foo&&b").split_rule("&&")

    def test_json_code_balance(self):
        # 代码平衡组：花括号/方括号内的 && 不算分隔符
        ra = RuleAnalyzer("$[?(@.a=='x&&y')]&&$..b", code=True)
        self.assertEqual(ra.split_rule("&&", "||"), ["$[?(@.a=='x&&y')]", "$..b"])

    def test_json_nested_brackets(self):
        ra = RuleAnalyzer("$[?(@.a[0]=='x')]||$..b", code=True)
        self.assertEqual(ra.split_rule("&&", "||"), ["$[?(@.a[0]=='x')]", "$..b"])


class InnerRuleTest(unittest.TestCase):
    def test_replace_inner(self):
        ra = RuleAnalyzer("[{$.a}]-[{$.b}]")
        result = ra.inner_rule("{$.", 1, 1, lambda r: {"$.a": "1", "$.b": "2"}.get(r, ""))
        self.assertEqual(result, "[1]-[2]")

    def test_no_replacement_returns_empty(self):
        ra = RuleAnalyzer("plain text")
        self.assertEqual(ra.inner_rule("{$.", 1, 1, lambda r: "x"), "")

    def test_pair_replace(self):
        ra = RuleAnalyzer("a{{x}}b")
        self.assertEqual(ra.inner_rule_pair("{{", "}}", lambda r: "X"), "aXb")


if __name__ == "__main__":
    unittest.main()
