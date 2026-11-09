"""AnalyzeRule 主流程测试：分隔符、替换、变量、模式判定、URL 绝对化。"""

import unittest

from legado_rule import AnalyzeRule, Mode, SourceRule


class SeparatorTest(unittest.TestCase):
    def setUp(self):
        self.html = (
            '<div class="a"><p class="t">甲</p><p class="t">乙</p>'
            '<span class="s">丙</span></div>'
        )
        self.rule = AnalyzeRule().set_content(self.html, "https://ex.com/x")

    def test_and_concatenates(self):
        self.assertEqual(self.rule.get_string("class.t@text&&class.s@text"), "甲\n乙\n丙")

    def test_or_falls_back(self):
        self.assertEqual(self.rule.get_string("class.none@text||class.s@text"), "丙")

    def test_percent_interleaves(self):
        self.assertEqual(self.rule.get_string_list("class.t@text%%class.s@text"), ["甲", "丙", "乙"])


class ModeTest(unittest.TestCase):
    HTML = "<div><a href='/x'>t</a></div>"

    def rule(self, text):
        return SourceRule(text, Mode.DEFAULT, AnalyzeRule().set_content(self.HTML, "https://e.com"))

    def test_prefix_order(self):
        self.assertEqual(self.rule("@CSS:.x@text").mode, Mode.DEFAULT)
        self.assertEqual(self.rule("@css:.a@text").mode, Mode.DEFAULT)
        self.assertEqual(self.rule("//div").mode, Mode.XPATH)
        self.assertEqual(self.rule("$.a").mode, Mode.JSON)
        self.assertEqual(self.rule("$[0]").mode, Mode.JSON)
        self.assertEqual(self.rule("@XPath://div").mode, Mode.XPATH)
        self.assertEqual(self.rule("@Json:$.a").mode, Mode.JSON)

    def test_css_prefix_not_stripped(self):
        # @CSS: 不剥前缀，交给 AnalyzeByJSoup 用 lastIndexOf('@') 自己切
        element_rule = self.rule("@CSS:.a@text")
        self.assertTrue(element_rule.rule.startswith("@CSS:"))

    def test_double_at_strips_prefix(self):
        self.assertEqual(self.rule("@@//div").rule, "//div")

    def test_regex_by_leading_colon(self):
        ar = AnalyzeRule().set_content("abc123", "https://e.com")
        rules = ar.split_source_rule(":\\d+", all_in_one=True)
        self.assertEqual(rules[0].mode, Mode.REGEX)
        self.assertEqual(rules[0].rule, "\\d+")

    def test_regex_flag(self):
        ar = AnalyzeRule().set_content("abc123", "https://e.com")
        ar.is_regex = True
        self.assertEqual(ar.get_string("\\d+"), "123")

    def test_js_split(self):
        ar = AnalyzeRule().set_content(self.HTML, "https://e.com")
        rules = ar.split_source_rule("a@text@js:result + '!'")
        self.assertEqual(rules[0].mode, Mode.DEFAULT)
        self.assertEqual(rules[1].mode, Mode.JS)


class ReplaceTest(unittest.TestCase):
    def setUp(self):
        self.rule = AnalyzeRule().set_content("<p class='t'>一二三</p>", "https://e.com")

    def test_replace_all(self):
        self.assertEqual(self.rule.get_string("class.t@text##[一二]##X"), "XX三")

    def test_invalid_regex_falls_back_to_literal(self):
        # 正则编译失败时退回"字面串替换"
        self.assertEqual(self.rule.get_string("class.t@text##[一二##X"), "一二三")

    def test_replace_first_variant(self):
        # 三段 && 后面还有 # => replaceFirst，只保留"首个匹配被替换后的片段"
        self.assertEqual(self.rule.get_string("class.t@text##一##A###"), "A")

    def test_no_match_first_returns_empty(self):
        self.assertEqual(self.rule.get_string("class.t@text##无##A###"), "")

    def test_group_reference_first(self):
        # 书源常见写法：##《([^》]+)》##$1### —— $1 是捕获组，不是字面量
        ar = AnalyzeRule().set_content("<p class='t'>《斗罗》大陆</p>", "https://e.com")
        self.assertEqual(ar.get_string("class.t@text##《([^》]+)》##$1###"), "斗罗")

    def test_group_reference_all(self):
        ar = AnalyzeRule().set_content("<p class='t'>a1b2</p>", "https://e.com")
        self.assertEqual(ar.get_string("class.t@text##([a-z])(\\d)##$2-$1"), "1-a2-b")

    def test_group_zero(self):
        ar = AnalyzeRule().set_content("<p class='t'>abc</p>", "https://e.com")
        self.assertEqual(ar.get_string("class.t@text##b##[$0]"), "a[b]c")

    def test_replace_removes(self):
        self.assertEqual(self.rule.get_string("class.t@text##二"), "一三")


class VariableTest(unittest.TestCase):
    def test_put_then_get(self):
        ar = AnalyzeRule().set_content("<p class='n'>书名</p>", "https://e.com")
        ar.put("bookName", ar.get_string("class.n@text"))
        self.assertEqual(ar.get("bookName"), "书名")

    def test_put_rule_populates_variable(self):
        ar = AnalyzeRule().set_content("<p class='n'>书名</p><p class='u'>作者</p>", "https://e.com")
        # @put:{key:"子规则"}：先把子规则的结果存进变量
        ar.get_string("@put:{bn:\"class.n@text\"}")
        self.assertEqual(ar.get("bn"), "书名")

    def test_eval_token_forces_regex_mode(self):
        # 怪行为：规则体里出现 {{ }} 会把整条规则切成 Regex，
        # 于是拼接后的 CSS 文本被当正则，匹配不到 -> 空串。
        ar = AnalyzeRule().set_content("<p class='n'>书名</p><p class='u'>作者</p>", "https://e.com")
        ar.put("bn", "书名")
        self.assertEqual(ar.get_string("class.u@text-{{java.get('bn')}}"), "")

    def test_dollar_param_from_list(self):
        ar = AnalyzeRule()
        ar.content = ["A", "B"]
        self.assertEqual(ar.get_string("$1"), "B")

    def test_dollar_param_when_not_list_keeps_literal(self):
        # 内容不是 list 时 $n 保留字面量；但 $n 又会把整条规则切成 Regex，
        # 于是 "$0" 被当正则匹配到末尾空串 -> 结果为空。
        ar = AnalyzeRule().set_content("plain", "https://e.com")
        self.assertEqual(ar.get_string("$0"), "")

    def test_unset_variable_is_empty(self):
        self.assertEqual(AnalyzeRule().get("nothing"), "")


class UrlTest(unittest.TestCase):
    def setUp(self):
        self.rule = AnalyzeRule().set_content(
            "<a href='/book/1'>x</a><img src='//cdn.ex.com/1.jpg'>", "https://ex.com/list/"
        )

    def test_relative(self):
        self.assertEqual(self.rule.get_string("tag.a@href", is_url=True), "https://ex.com/book/1")

    def test_protocol_relative(self):
        self.assertEqual(
            self.rule.get_string("tag.img@src", is_url=True), "https://cdn.ex.com/1.jpg"
        )

    def test_empty_falls_back_to_base(self):
        self.assertEqual(self.rule.get_string("class.none@href", is_url=True), "https://ex.com/list/")

    def test_unescape_html_entity(self):
        rule = AnalyzeRule().set_content('<a href="?a=1&amp;b=2">x</a>', "https://ex.com")
        self.assertEqual(rule.get_string("tag.a@href"), "?a=1&b=2")


if __name__ == "__main__":
    unittest.main()
