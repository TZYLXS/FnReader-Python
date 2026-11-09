"""JSONPath 与 XPath 求值测试。"""

import unittest

from legado_rule import AnalyzeRule

JSON_TEXT = """
{
  "code": 0,
  "data": {
    "book": {"name": "斗罗大陆", "author": "唐家三少", "tags": ["玄幻", "热血"], "words": 3200000},
    "chapters": [
      {"title": "第一章", "url": "/c/1", "vip": false},
      {"title": "第二章", "url": "/c/2", "vip": true},
      {"title": "第三章", "url": "/c/3", "vip": true}
    ]
  }
}
"""


class JsonPathTest(unittest.TestCase):
    def setUp(self):
        self.rule = AnalyzeRule().set_content(JSON_TEXT, "https://api.ex.com/book")

    def test_dotted(self):
        self.assertEqual(self.rule.get_string("$.data.book.name"), "斗罗大陆")

    def test_array_index(self):
        self.assertEqual(self.rule.get_string("$.data.chapters[1].title"), "第二章")

    def test_wildcard_list(self):
        self.assertEqual(self.rule.get_string_list("$.data.chapters[*].title"), ["第一章", "第二章", "第三章"])

    def test_recursive_descent(self):
        self.assertEqual(self.rule.get_string("$..author"), "唐家三少")

    def test_slice(self):
        self.assertEqual(self.rule.get_string_list("$.data.chapters[0:2].title"), ["第一章", "第二章"])

    def test_filter(self):
        self.assertEqual(self.rule.get_string_list("$.data.chapters[?(@.vip==true)].title"), ["第二章", "第三章"])

    def test_union(self):
        self.assertEqual(self.rule.get_string_list("$.data.chapters[0,2].title"), ["第一章", "第三章"])

    def test_function_length(self):
        self.assertEqual(self.rule.get_string("$.data.chapters.length()"), "3")

    def test_json_prefix(self):
        self.assertEqual(self.rule.get_string("@Json:$.code"), "0")

    def test_native_object_branch(self):
        # 内容已是 dict 时走 NativeObject 分支，规则直接当键名
        import json
        data = json.loads(JSON_TEXT)["data"]["book"]
        rule = AnalyzeRule().set_content(data, "")
        # 内容已是对象时规则走 Json 模式；裸键名在此实现里被宽松地补成 $.name
        # （jayway 严格模式会报错，属于有意的超集，便于兼容 @js 产出的对象列表）
        self.assertEqual(rule.get_string("$.name"), "斗罗大陆")
        self.assertEqual(rule.get_string("name"), "斗罗大陆")
        self.assertEqual(rule.get_string("$.author"), "唐家三少")


class XPathTest(unittest.TestCase):
    HTML = (
        '<html><body><div class="list">'
        '<p class="item"><a href="/b/1">第一本</a></p>'
        '<p class="item"><a href="/b/2">第二本</a></p>'
        "</div></body></html>"
    )

    def setUp(self):
        self.rule = AnalyzeRule().set_content(self.HTML, "https://ex.com")

    def test_text(self):
        self.assertEqual(self.rule.get_string("//p[@class='item'][1]/a/text()"), "第一本")

    def test_element_as_string_is_outer_html(self):
        value = self.rule.get_string("//p[@class='item'][1]")
        self.assertEqual(value, '<p class="item"><a href="/b/1">第一本</a></p>')

    def test_attribute(self):
        # 多个节点命中时按 \n 拼接
        self.assertEqual(self.rule.get_string("//p/a/@href"), "/b/1\n/b/2")

    def test_list(self):
        self.assertEqual(self.rule.get_string_list("//p[@class='item']/a/text()"), ["第一本", "第二本"])

    def test_and_or(self):
        self.assertEqual(self.rule.get_string("//none/text() && //p[1]/a/text()"), "第一本")
        self.assertEqual(self.rule.get_string("//none/text() || //p[2]/a/text()"), "第二本")

    def test_xpath_prefix(self):
        self.assertEqual(self.rule.get_string("@XPath://p[@class='item'][2]/a/text()"), "第二本")

    def test_td_wrapping(self):
        # 规则以 </td> 结尾时 会包一层 <tr>，否则 XPath 解析不出根节点
        rule = AnalyzeRule().set_content('<td class="c">单元格</td>', "https://ex.com")
        self.assertEqual(rule.get_string("//td[@class='c']/text()"), "单元格")


if __name__ == "__main__":
    unittest.main()
