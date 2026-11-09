"""接口总演示：不联网，一次跑完所有对外接口。

    python examples/api_demo.py

输出可直接与《接口说明.md》里的"预期输出"逐行对照。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legado_rule import (  # noqa: E402
    AnalyzeRule,
    BookSourceEngine,
    JsEngine,
    RuleAnalyzer,
    __version__,
)

HTML = """<div class="book" id="main">
  <h1 class="title">斗罗大陆</h1>
  <p class="author">唐家三少</p>
  <ul class="list">
    <li><a href="/c/1">第一章 觉醒</a><span class="no">1</span></li>
    <li><a href="/c/2">第二章 武魂</a><span class="no">2</span></li>
    <li><a href="/c/3">第三章 学院</a><span class="no">3</span></li>
    <li><a href="/c/4">第四章 考试</a><span class="no">4</span></li>
  </ul>
  <div class="text">第一段<br>第二段<br><script>var a=1;</script>第三段</div>
  <div class="selfclose">前<a/>后</div>
</div>"""


def show(label: str, value) -> None:
    print(f"  {label:<44} -> {json.dumps(value, ensure_ascii=False)}")


def section(title: str) -> None:
    print(f"\n[{title}]")


# ---------------------------------------------------------------- #
# 1. 环境自检
# ---------------------------------------------------------------- #
def demo_env() -> None:
    section("1 环境自检")
    show("legado_rule.__version__", __version__)
    show("JS 引擎后端", JsEngine().backend_name)


# ---------------------------------------------------------------- #
# 2. 规则级：AnalyzeRule
# ---------------------------------------------------------------- #
def demo_rule_level() -> None:
    section("2 基础取值")
    rule = AnalyzeRule().set_content(HTML, "https://demo.test/book/1")
    show("get_string('class.title@text')", rule.get_string("class.title@text"))
    show("get_string('class.list@tag.a@text')", rule.get_string("class.list@tag.a@text"))
    show("get_string_list('class.list@tag.a@text')", rule.get_string_list("class.list@tag.a@text"))
    show("get_string_list('tag.a@href', is_url=True)", rule.get_string_list("class.list@tag.a@href", is_url=True))
    show("get_elements('class.list@tag.li') 个数", len(rule.get_elements("class.list@tag.li")))
    show("get_elements 元素类型", type(rule.get_elements("tag.a")[0]).__name__)

    section("3 取值尾缀")
    show("class.text@text", rule.get_string("class.text@text"))
    show("class.text@textNodes", rule.get_string("class.text@textNodes"))
    show("class.text@html（已去 script）", rule.get_string("class.text@html"))
    show("class.selfclose@textNodes", rule.get_string("class.selfclose@textNodes"))

    section("4 索引语法")
    show("tag.a.1", rule.get_string_list("class.list@tag.a.1@text"))
    show("tag.a!1（排除）", rule.get_string_list("class.list@tag.a!1@text"))
    show("tag.a[1,3]", rule.get_string_list("class.list@tag.a[1,3]@text"))
    show("tag.a[1:3]（闭区间）", rule.get_string_list("class.list@tag.a[1:3]@text"))
    show("tag.a[-1,0]（反向）", rule.get_string_list("class.list@tag.a[-1,0]@text"))
    show("tag.a!0:2", rule.get_string_list("class.list@tag.a!0:2@text"))

    section("5 分隔符与替换")
    show("&& 串联", rule.get_string("class.title@text&&class.author@text"))
    show("|| 回退", rule.get_string("class.none@text||class.title@text"))
    show("RuleAnalyzer('a&&b||c') 首分隔符锁定", RuleAnalyzer("a&&b||c").split_rule("&&", "||", "%%"))
    show("##正则##替换##", rule.get_string("class.title@text##大陆##帝国##"))
    show("### 只替首个（无匹配返回空）", rule.get_string("class.text@textNodes###段##行###"))

    section("6 模式前缀")
    show("@CSS:.title@text", rule.get_string("@CSS:.title@text"))
    show("@@.title@text", rule.get_string("@@.title@text"))
    show("@XPath://h1/text()", rule.get_string("@XPath://h1/text()"))
    show("/html/body/div/h1/text()（隐式 XPath）", rule.get_string("/html/body/div/h1/text()"))

    section("7 变量与 JS")
    show("@put:{n:'class.title@text'}@get:{n}", rule.get_string("@put:{n:'class.title@text'}@get:{n}"))
    show("set_local('page',3) -> @js:page", (rule.set_local("page", "3"), rule.get_string("@js:String(page)"))[1])
    show("@js:java.getString('class.title@text')", rule.get_string("@js:java.getString('class.title@text')"))
    show("@js:java.put + java.get", rule.get_string("@js:(java.put('k','v'), java.get('k'))"))
    show("@js:正则提取", rule.get_string("@js:/第二章/.test(result)"))

    section("8 JSON / JSONPath")
    data = {"data": {"books": [{"name": "书A", "author": "作者A"}, {"name": "书B", "author": "作者B"}]}}
    jrule = AnalyzeRule().set_content(data, "https://demo.test/api")
    show("$.data.books[*].name", jrule.get_string_list("$.data.books[*].name"))
    show("$..name", jrule.get_string_list("$..name"))
    show("$.data.books[?(@.name=='书B')].author", jrule.get_string("$.data.books[?(@.name=='书B')].author"))
    show("$.data.books.length()", jrule.get_string("$.data.books.length()"))
    show("@Json:$.data.books[?(@.name=='书B')].author", jrule.get_string("@Json:$.data.books[?(@.name=='书B')].author"))

    section("9 反直觉但必须保留的语义")
    show("{{ }} 使整条规则变成 Regex 模式", rule.get_string("class.title@text-{{java.get('none')}}"))


# ---------------------------------------------------------------- #
# 3. 书源级：BookSourceEngine（离线 fetcher）
# ---------------------------------------------------------------- #
PAGES = {
    "http://m.test.com/search/?q=%E5%89%91%E6%9D%A5": """<div class="res"><ul>
        <li><a href="/b/1">剑来</a><i>烽火戏诸侯</i></li>
        <li><a href="/b/2">雪中悍刀行</a><i>烽火戏诸侯</i></li>
      </ul></div>""",
    "http://m.test.com/b/1": """<div class="info"><h1>剑来</h1><p class="au">烽火戏诸侯</p>
        <p class="intro">大千世界，无奇不有。</p><a class="toc" href="/b/1/toc">目录</a></div>""",
    "http://m.test.com/b/1/toc": """<ul class="list">
        <li><a href="/b/1/c/1">第一章 雪夜</a></li>
        <li><a href="/b/1/c/2">第二章 走山</a></li></ul>""",
    "http://m.test.com/b/1/c/1": """<div id="content"><p>第一章正文第一段。</p>
        <p>第一章正文第二段。</p><a href="/b/1/c/2">下一章</a></div>""",
}

SOURCE = {
    "bookSourceName": "测试源",
    "bookSourceUrl": "http://m.test.com",
    "searchUrl": "http://m.test.com/search/?q={{key}}",
    "ruleSearch": {"bookList": "class.res@tag.li", "name": "tag.a@text",
                   "author": "tag.i@text", "bookUrl": "tag.a@href"},
    "ruleBookInfo": {"name": "class.info@tag.h1@text", "author": "class.au@text",
                     "intro": "class.intro@text", "tocUrl": "class.toc@href"},
    "ruleToc": {"chapterList": "class.list@tag.li", "chapterName": "tag.a@text",
                "chapterUrl": "tag.a@href"},
    "ruleContent": {"content": "id.content@text", "nextContentUrl": "tag.a@href"},
}


def demo_engine() -> None:
    section("10 书源引擎（离线 fetcher）")
    calls = []

    def fake_fetch(url, method="GET", headers=None, body=None, charset=None):
        calls.append(url)
        return PAGES.get(url, "")

    engine = BookSourceEngine(SOURCE, fetcher=fake_fetch)

    books = engine.search("剑来")
    show("search('剑来')", books[:1])
    show("search 条目数", len(books))

    info = engine.book_info(books[0]["bookUrl"])
    show("book_info(bookUrl)", info)

    chapters = engine.chapters(info["tocUrl"])
    show("chapters(tocUrl)", chapters)

    body = engine.content(chapters[0]["url"])
    show("content(chapterUrl)", body)

    show("请求过的 URL", calls)
    show("last_error", engine.last_error)

    section("11 异常降级")
    def boom(url, method="GET", headers=None, body=None, charset=None):
        raise RuntimeError("network down")

    bad = BookSourceEngine(SOURCE, fetcher=boom)
    show("search()（fetcher 抛错）", bad.search("剑来"))
    show("last_error", bad.last_error)


def main() -> None:
    demo_env()
    demo_rule_level()
    demo_engine()
    print("\n全部接口跑通。")


if __name__ == "__main__":
    main()
