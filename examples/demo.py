"""示例：书源 → 前端参数。

两种用法：
1. 真实联网（默认）：直接跑，输出搜索/详情/目录/正文的 JSON；
2. 离线：把 fetcher 换成读本地 HTML 的函数（见 tests/test_engine.py）。

运行：
    python examples/demo.py                  # 用内置示例书源联网搜索「剑来」
    python examples/demo.py <书源.json> 关键字
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legado_rule import AnalyzeRule, BookSourceEngine

# 一个最小可用的书源（真实站点：顶点小说，仅作演示，规则随站点改版可能失效）
SAMPLE_SOURCE = {
    "bookSourceName": "顶点小说（示例）",
    "bookSourceUrl": "http://www.ddxsku.com",
    "searchUrl": "http://www.ddxsku.com/search/?searchkey={{key}}",
    "ruleSearch": {
        "bookList": "tag.table@tag.tr!0",
        "name": "tag.td.0@tag.a.0@text",
        "author": "tag.td.2@text",
        "bookUrl": "tag.td.0@tag.a.0@href",
        "lastChapter": "tag.td.1@tag.a.0@text",
    },
    "ruleBookInfo": {"name": "tag.a.16@text"},
    "ruleToc": {"chapterList": "id.at@tag.td@tag.a", "chapterName": "text", "chapterUrl": "href"},
    "ruleContent": {"content": "id.contents@html"},
}


def rule_level_demo() -> None:
    """不联网：只演示单条规则的求值。"""
    html = """
    <div class="book">
      <h1 class="title">斗罗大陆</h1>
      <p class="author">唐家三少</p>
      <ul class="list">
        <li><a href="/c/1">第一章</a></li>
        <li><a href="/c/2">第二章</a></li>
      </ul>
    </div>
    """
    rule = AnalyzeRule().set_content(html, "https://demo.test/book/1")
    print("书名 :", rule.get_string("class.title@text"))
    print("作者 :", rule.get_string("class.author@text"))
    print("章节 :", rule.get_string_list("class.list@tag.li@tag.a@text"))
    print("链接 :", rule.get_string_list("class.list@tag.li@tag.a@href", is_url=True))
    print("净化 :", rule.get_string("class.title@text##[斗罗]##"))


def source_demo(source: dict, keyword: str) -> None:
    engine = BookSourceEngine(source)

    books = engine.search(keyword)
    print(f"\n搜索「{keyword}」：{len(books)} 条")
    if books:
        print(json.dumps(books[0], ensure_ascii=False, indent=2))

        info = engine.book_info(books[0]["bookUrl"])
        print("详情：", info.get("name"), "| 目录地址：", info.get("tocUrl"))

        chapters = engine.chapters(info["tocUrl"])
        print(f"目录：{len(chapters)} 章；前三：{[c['title'] for c in chapters[:3]]}")

        if chapters:
            body = engine.content(chapters[0]["url"])
            print("正文字符数：", len(body["content"]))

    if engine.last_error:
        print("错误：", engine.last_error)


def main() -> None:
    rule_level_demo()

    if len(sys.argv) >= 2:
        with open(sys.argv[1], encoding="utf-8") as fh:
            data = json.load(fh)
        source = data[0] if isinstance(data, list) else data
        keyword = sys.argv[2] if len(sys.argv) > 2 else "剑来"
        source_demo(source, keyword)
    else:
        print("\n（联网演示需要真实书源：python examples/demo.py 书源.json 关键字）")
        print("（离线端到端见 tests/test_engine.py）")


if __name__ == "__main__":
    main()
