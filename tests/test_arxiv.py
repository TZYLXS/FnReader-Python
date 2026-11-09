"""arXiv API 书源离线测试。

用真实 arXiv Atom XML 作为测试数据，验证 BookSourceEngine 能用 XPath 规则
从 XML 里解析出论文条目。不联网，直接读 examples 下的真实响应样本。
"""

import json
import os
import unittest

from legado_rule import BookSourceEngine

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SOURCE = json.load(open(os.path.join(ROOT, "examples", "arxiv_source.json"), encoding="utf-8"))
ARXIV_XML = open(os.path.join(ROOT, "_arxiv.xml"), encoding="utf-8").read()


class ArxivTest(unittest.TestCase):
    def setUp(self):
        def fetcher(url, method="GET", headers=None, body=None, charset=None):
            return ARXIV_XML

        self.engine = BookSourceEngine(SOURCE, fetcher=fetcher)

    def test_search_url(self):
        url, method, body = self.engine.build_search_url("machine learning", 1)
        self.assertIn("search_query=all:", url)
        self.assertIn("start=0", url)

    def test_search_url_page2(self):
        url, method, body = self.engine.build_search_url("test", 2)
        self.assertIn("start=10", url)

    def test_search_parses_results(self):
        books = self.engine.search("machine learning")
        self.assertGreater(len(books), 0, "should parse at least one entry")
        first = books[0]
        print("first:", first)
        self.assertTrue(first["name"].strip(), "name should not be empty")
        self.assertTrue(first["author"].strip(), "author should not be empty")
        self.assertTrue(first["intro"].strip(), "intro should not be empty")
        self.assertTrue(first["bookUrl"].startswith("http://arxiv.org/abs/"))

    def test_book_info(self):
        # 用搜索结果里的第一个 bookUrl 跑详情
        books = self.engine.search("machine learning")
        info = self.engine.book_info(books[0]["bookUrl"])
        self.assertTrue(info["name"].strip())
        self.assertTrue(info["intro"].strip())


if __name__ == "__main__":
    unittest.main()
