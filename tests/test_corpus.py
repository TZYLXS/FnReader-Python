"""真实书源库回归：把 yuedushuyuan 的 17,077 条书源的每条规则都过一遍解析器。

只验证"不崩 + 模式分布合理"，不联网。语料不在时自动跳过。
"""

import glob
import json
import os
import unittest
from collections import Counter

from legado_rule import AnalyzeRule

CORPUS = os.path.expanduser("~/Doubao/chats/38452634578730242/sources/yuedushuyuan-master")

RULE_KEYS = [
    "ruleSearchList", "ruleSearchName", "ruleSearchAuthor", "ruleSearchKind",
    "ruleSearchLastChapter", "ruleSearchIntroduce", "ruleSearchCoverUrl", "ruleSearchNoteUrl",
    "ruleBookName", "ruleBookAuthor", "ruleBookKind", "ruleBookLastChapter", "ruleIntroduce",
    "ruleCoverUrl", "ruleChapterUrl", "ruleBookContent", "ruleContentUrlNext",
    "ruleChapterList", "ruleChapterName", "exploreUrl", "ruleReview",
]


@unittest.skipUnless(os.path.isdir(CORPUS), "没有本地书源语料，跳过")
class CorpusTest(unittest.TestCase):
    def test_all_rules_parse(self):
        sources = 0
        rules = 0
        modes = Counter()
        failures = []
        for path in sorted(glob.glob(os.path.join(CORPUS, "*.json"))):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for source in data:
                sources += 1
                for key in RULE_KEYS:
                    value = source.get(key)
                    if not isinstance(value, str) or not value:
                        continue
                    rules += 1
                    try:
                        analyzer = AnalyzeRule()
                        for rule in analyzer.split_source_rule(value):
                            modes[rule.mode.name] += 1
                    except Exception as exc:  # noqa: BLE001
                        failures.append((source.get("bookSourceName"), key, str(exc)))

        self.assertGreater(sources, 10000)
        self.assertEqual(failures, [])
        # 默认模式必须占多数，否则说明模式判定跑偏了
        self.assertGreater(modes["DEFAULT"], modes["REGEX"])


if __name__ == "__main__":
    unittest.main()
