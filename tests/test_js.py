"""JS 规则测试（quickjs 沙箱）。

规则里注入的变量名是固定的一套：``result`` / ``baseUrl`` / ``src`` /
``book`` / ``chapter`` / ``page`` …，以及一个带 ``java.*`` 方法的壳对象。
"""

import unittest

from legado_rule import AnalyzeRule, JsEngine


class JsRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = AnalyzeRule().set_content('{"n": 3, "s": "文本"}', "https://ex.com/api")

    def test_js_prefix_with_result(self):
        self.assertEqual(self.rule.get_string("@js:JSON.parse(result).s"), "文本")

    def test_js_tag_form(self):
        self.assertEqual(self.rule.get_string("<js>JSON.parse(src).n * 2</js>"), "6")

    def test_js_uses_base_url(self):
        self.assertEqual(self.rule.get_string("@js:baseUrl + '/x'"), "https://ex.com/api/x")

    def test_js_returns_object(self):
        value = self.rule.get_string("@js:({a: 1})")
        self.assertEqual(value, '{"a": 1}')

    def test_js_returns_boolean_and_float(self):
        rule = AnalyzeRule().set_content("x", "https://e.com")
        self.assertEqual(rule.get_string("@js:1 == 1"), "true")
        # JSON 桥会把 2.0 变成整数 2（Double 2.0 -> "2.0"，此处为已知微小差异）
        self.assertEqual(rule.get_string("@js:2.0"), "2")

    def test_java_get_string_on_content(self):
        rule = AnalyzeRule().set_content(
            '<p class="t">书名</p>', "https://e.com"
        )
        self.assertEqual(rule.get_string("@js:java.getString('class.t@text')"), "书名")

    def test_java_put_then_get(self):
        rule = AnalyzeRule().set_content('<p class="t">书名</p>', "https://e.com")
        self.assertEqual(rule.get_string("@js:java.put('k', 'v')"), "v")
        self.assertEqual(rule.get("k"), "v")

    def test_java_get_string_list(self):
        rule = AnalyzeRule().set_content(
            '<a class="c">1</a><a class="c">2</a>', "https://e.com"
        )
        value = rule.get_string("@js:java.getStringList('class.c@text').join('|')")
        self.assertEqual(value, "1|2")

    def test_page_binding_is_number(self):
        rule = AnalyzeRule().set_content("x", "https://e.com")
        rule.set_local("page", "3")
        self.assertEqual(rule.get_string("@js:page + 1"), "4")

    def test_error_surfaces(self):
        with self.assertRaises(Exception):
            self.rule.get_string("@js:undefinedFn()")


class JsEngineTest(unittest.TestCase):
    def test_backend_name(self):
        self.assertIn(JsEngine().backend_name, ("quickjs", "node"))

    def test_eval_plain(self):
        self.assertEqual(JsEngine().eval("1 + 2"), 3)

    def test_json_bridge(self):
        self.assertEqual(
            JsEngine().eval("JSON.parse(src).a[1]", {"src": '{"a":[1,2]}'}), 2
        )


if __name__ == "__main__":
    unittest.main()
