"""CSS / DOM 求值器测试。

前半部分移植 ``AnalyzeByJSoupDomTest.kt``（自闭合标签、
textNodes 语义、节点不被规则改动、排除式索引），后半部分是索引与尾缀的补充。
"""

import unittest

from legado_rule import AnalyzeByJSoup, AnalyzeRule


def ids(elements):
    return [el.get("id") for el in elements]


class DomSemanticsTest(unittest.TestCase):
    def test_self_closing_anchor_preserves_text_nodes(self):
        html = (
            '<div class="chapter_content">您现在阅读的是'
            '<a href="https://www.303wx.com">303文学<a/>'
            "www.303wx.com提供的《示例》<br>正文第一段<br>正文第二段</div>"
        )
        values = AnalyzeByJSoup(html).get_string(".chapter_content@textNodes")
        self.assertIn("正文第一段\n正文第二段", values)

    def test_text_nodes_exclude_descendant_text(self):
        parser = AnalyzeByJSoup("<div>before<a>link</a><span>nested</span>after</div>")
        self.assertEqual(parser.get_string("div@textNodes"), "before\nafter")
        self.assertEqual(parser.get_string("a@text"), "link")
        self.assertEqual(parser.get_string("span@text"), "nested")

    def test_custom_self_closing_tag(self):
        self.assertEqual(
            AnalyzeByJSoup("<div><custom/>after</div>").get_string("div@textNodes"),
            "after",
        )

    def test_reading_name_does_not_replace_link(self):
        html = """
        <div class="row">
            <span><a href="/posts/11946">Book title</a></span>
            <span class="pull-right smaller-5"><a href="/users/456925">Author</a></span>
        </div>
        """
        parser = AnalyzeByJSoup(html)
        self.assertEqual(parser.get_string("tag.span.0@tag.a.0@text"), "Book title")
        self.assertEqual(parser.get_string("class.pull-right smaller-5@text"), "Author")
        self.assertEqual(parser.get_string("class.row@tag.span.0@tag.a.-1@href"), "/posts/11946")

    def test_forum_title_with_entity_and_fallback(self):
        html = """
        <table><tr>
            <th><a href="/forum.php?mod=forumdisplay&amp;fid=19">Category</a>
                <a class="bui_thlist_title" href="/forum.php?mod=viewthread&amp;tid=5276">Thread title</a>
            </th>
            <td class="by"><a href="/home.php?mod=space&amp;uid=2411">Author</a></td>
        </tr></table>
        """
        parser = AnalyzeByJSoup(html)
        self.assertEqual(parser.get_string("th@.bui_thlist_title@text||th@a.0@text"), "Thread title")
        self.assertEqual(parser.get_string(".by.0@a.0@text||a.2@text"), "Author")
        self.assertEqual(
            parser.get_string("th@a.1@href"), "/forum.php?mod=viewthread&tid=5276"
        )

    def test_chained_selection_keeps_document(self):
        document = AnalyzeByJSoup("<div class=list><p><a href='/book'>Book</a></p></div>")
        before = document.get_string("class.list@html")
        self.assertEqual(len(document.get_elements("class.list@tag.p@tag.a")), 1)
        self.assertEqual(document.get_string("class.list@html"), before)

    def test_excluding_indexes_do_not_touch_dom(self):
        html = "<p><a id=a>A</a><a id=b>B</a><a id=c>C</a></p>"
        cases = {
            "tag.a!0:2": ["b"],
            "tag.a[!0,-1]": ["b"],
            "tag.a!1": ["a", "c"],
        }
        for rule, expected in cases.items():
            parser = AnalyzeByJSoup(html)
            self.assertEqual(ids(parser.get_elements(rule)), expected, rule)
            self.assertEqual(ids(parser.get_elements("tag.a")), ["a", "b", "c"])

    def test_positive_and_negative_indexes(self):
        parser = AnalyzeByJSoup("<p><a id=a>A</a><a id=b>B</a><a id=c>C</a></p>")
        self.assertEqual(ids(parser.get_elements("tag.a[-1,0]")), ["c", "a"])
        self.assertEqual(ids(parser.get_elements("tag.a.0")), ["a"])

    def test_range_slice(self):
        parser = AnalyzeByJSoup("<p><a id=a>A</a><a id=b>B</a><a id=c>C</a><a id=d>D</a></p>")
        self.assertEqual(ids(parser.get_elements("tag.a[1:3]")), ["b", "c", "d"])
        self.assertEqual(ids(parser.get_elements("tag.a[0:4:2]")), ["a", "c"])
        self.assertEqual(ids(parser.get_elements("tag.a[-1:0]")), ["d", "c", "b", "a"])


class GetterTest(unittest.TestCase):
    HTML = (
        '<div class="box"><h1>标题</h1>'
        '<p class="p">段落<b>粗</b>尾</p>'
        '<script>var a=1;</script><style>.x{}</style>'
        '<img src="/img/1.jpg"></div>'
    )

    def setUp(self):
        self.rule = AnalyzeRule().set_content(self.HTML, "https://example.com/book/1")

    def test_text(self):
        self.assertEqual(self.rule.get_string("tag.h1@text"), "标题")

    def test_own_text(self):
        self.assertEqual(self.rule.get_string("class.p@ownText"), "段落尾")

    def test_html_strips_script_and_style(self):
        html = self.rule.get_string("class.box@html")
        self.assertNotIn("<script", html)
        self.assertNotIn("<style", html)
        self.assertIn("<h1>标题</h1>", html)

    def test_all_keeps_tags(self):
        self.assertIn("<script", self.rule.get_string("class.box@all"))

    def test_attr_and_absolute_url(self):
        self.assertEqual(self.rule.get_string("tag.img@src"), "/img/1.jpg")
        self.assertEqual(
            self.rule.get_string("tag.img@src", is_url=True), "https://example.com/img/1.jpg"
        )

    def test_css_prefix(self):
        self.assertEqual(self.rule.get_string("@CSS:.box h1@text"), "标题")

    def test_missing_getter_returns_empty(self):
        self.assertEqual(self.rule.get_string("class.box"), "")


if __name__ == "__main__":
    unittest.main()
