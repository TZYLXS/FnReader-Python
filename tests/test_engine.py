"""端到端：书源 → 前端参数（完全离线，用固定 HTML 当"网络"）。

验证的是"整条链路能不能把规则跑通并吐出干净的结构化数据"，不依赖真实站点。
"""

import unittest

from legado_rule import BookSourceEngine

SEARCH_HTML = """
<ul class="result">
  <li>
    <a href="/book/1">书一</a>
    <span class="au">甲作者</span>
    <span class="kind">玄幻</span>
    <span class="last">第十章 大结局</span>
    <p class="intro">简介一</p>
    <img src="/img/1.jpg">
  </li>
</ul>
"""

BOOK_HTML = """
<h1 class="title">书一</h1>
<span class="author">甲作者</span>
<img class="cover" src="/img/1.jpg">
<a class="toc" href="/book/1/toc">目录</a>
<p class="desc">这里是一本书的简介</p>
"""

TOC_HTML = """
<ul class="list">
  <li><a href="/c/1">第一章 开端</a></li>
  <li><a href="/c/2">第二章 发展</a></li>
</ul>
"""

CONTENT_HTML = """
<div id="content"><p>正文第一段</p><p>正文第二段</p></div>
<a class="next" href="/c/2">下一章</a>
"""


def make_fetcher(pages):
    calls = []

    def fetch(url, method="GET", headers=None, body=None, charset=None):
        calls.append(url)
        return pages.get(url, "<html><body>404</body></html>")

    fetch.calls = calls
    return fetch


GROUPED_SOURCE = {
    "bookSourceName": "示例站",
    "bookSourceUrl": "https://demo.test",
    "searchUrl": "/search?q={{key}}&page={{page}}",
    "ruleSearch": {
        "bookList": "class.result@tag.li",
        "name": "tag.a.0@text",
        "author": "class.au@text",
        "kind": "class.kind@text",
        "lastChapter": "class.last@text",
        "intro": "class.intro@text",
        "coverUrl": "tag.img@src",
        "bookUrl": "tag.a.0@href",
    },
    "ruleBookInfo": {
        "name": "class.title@text",
        "author": "class.author@text",
        "coverUrl": "class.cover@src",
        "tocUrl": "class.toc@href",
        "intro": "class.desc@text",
    },
    "ruleToc": {
        "chapterList": "class.list@tag.li",
        "chapterName": "tag.a@text",
        "chapterUrl": "tag.a@href",
    },
    "ruleContent": {
        "content": "id.content@html",
        "nextContentUrl": "class.next@href",
    },
}

PAGES = {
    "https://demo.test/search?q=%E6%96%97%E7%BD%97&page=1": SEARCH_HTML,
    "https://demo.test/book/1": BOOK_HTML,
    "https://demo.test/book/1/toc": TOC_HTML,
    "https://demo.test/c/1": CONTENT_HTML,
}


class GroupedRuleTest(unittest.TestCase):
    def setUp(self):
        self.engine = BookSourceEngine(GROUPED_SOURCE, fetcher=make_fetcher(PAGES))

    def test_search(self):
        books = self.engine.search("斗罗")
        self.assertEqual(len(books), 1)
        book = books[0]
        self.assertEqual(book["name"], "书一")
        self.assertEqual(book["author"], "甲作者")
        self.assertEqual(book["kind"], "玄幻")
        self.assertEqual(book["lastChapter"], "第十章 大结局")
        self.assertEqual(book["intro"], "简介一")
        self.assertEqual(book["bookUrl"], "https://demo.test/book/1")
        self.assertEqual(book["coverUrl"], "https://demo.test/img/1.jpg")
        self.assertEqual(book["origin"], "https://demo.test")

    def test_book_info_and_toc_url(self):
        info = self.engine.book_info("https://demo.test/book/1")
        self.assertEqual(info["name"], "书一")
        self.assertEqual(info["author"], "甲作者")
        self.assertEqual(info["intro"], "这里是一本书的简介")
        self.assertEqual(info["tocUrl"], "https://demo.test/book/1/toc")

    def test_chapters(self):
        chapters = self.engine.chapters("https://demo.test/book/1/toc")
        self.assertEqual([c["title"] for c in chapters], ["第一章 开端", "第二章 发展"])
        self.assertEqual(
            [c["url"] for c in chapters],
            ["https://demo.test/c/1", "https://demo.test/c/2"],
        )
        self.assertEqual(chapters[0]["index"], 0)

    def test_content(self):
        result = self.engine.content("https://demo.test/c/1")
        self.assertIn("<p>正文第一段</p>", result["content"])
        self.assertNotIn("<html", result["content"])
        self.assertEqual(result["nextContentUrl"], "https://demo.test/c/2")

    def test_search_url_encodes_key(self):
        self.engine.search("斗罗")
        self.assertIn("q=%E6%96%97%E7%BD%97", self.engine.fetcher.calls[0])


class FlatRuleTest(unittest.TestCase):
    """老式扁平字段（ruleSearchList / ruleBookContent …）必须同样可用。"""

    FLAT = {
        "bookSourceName": "扁平站",
        "bookSourceUrl": "https://demo.test",
        "searchUrl": "/search?q={{key}}&page={{page}}",
        "ruleSearchList": "class.result@tag.li",
        "ruleSearchName": "tag.a.0@text",
        "ruleSearchAuthor": "class.au@text",
        "ruleSearchNoteUrl": "tag.a.0@href",
        "ruleSearchCoverUrl": "tag.img@src",
        "ruleBookName": "class.title@text",
        "ruleChapterUrl": "class.toc@href",
        "ruleChapterList": "class.list@tag.li",
        "ruleChapterName": "tag.a@text",
        "ruleChapterUrl": "tag.a@href",
        "ruleBookContent": "id.content@text",
        "ruleContentUrlNext": "class.next@href",
    }

    def setUp(self):
        self.engine = BookSourceEngine(self.FLAT, fetcher=make_fetcher(PAGES))

    def test_search_flat(self):
        books = self.engine.search("斗罗")
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["name"], "书一")
        self.assertEqual(books[0]["bookUrl"], "https://demo.test/book/1")

    def test_group_takes_priority_over_flat(self):
        source = dict(self.FLAT)
        source["ruleToc"] = {"chapterList": "class.list@tag.a"}
        engine = BookSourceEngine(source, fetcher=make_fetcher(PAGES))
        chapters = engine.chapters("https://demo.test/book/1/toc")
        self.assertEqual(len(chapters), 2)  # 分组规则命中 a 标签

    def test_content_flat_uses_text(self):
        result = self.engine.content("https://demo.test/c/1")
        self.assertIn("正文第一段", result["content"])


class UrlRuleTest(unittest.TestCase):
    def test_js_search_url(self):
        source = {
            "bookSourceName": "js站",
            "bookSourceUrl": "https://demo.test",
            "searchUrl": "@js:'/search?q=' + key + '&page=' + page",
        }
        engine = BookSourceEngine(source, fetcher=lambda *a, **k: SEARCH_HTML)
        url, method, body = engine.build_search_url("斗罗", 2)
        self.assertEqual(url, "/search?q=斗罗&page=2")
        self.assertEqual(method, "GET")

    def test_options_suffix(self):
        source = {
            "bookSourceUrl": "https://demo.test",
            "searchUrl": '/search,{"method":"POST","body":"q={{key}}"}',
        }
        engine = BookSourceEngine(source, fetcher=lambda *a, **k: "")
        url, method, body = engine.build_search_url("a b")
        self.assertEqual(url, "https://demo.test/search")  # 相对地址按 bookSourceUrl 补全
        self.assertEqual(method, "POST")
        self.assertEqual(body, "q=a%20b")


if __name__ == "__main__":
    unittest.main()
