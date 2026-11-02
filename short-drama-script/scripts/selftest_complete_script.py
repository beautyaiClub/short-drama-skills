#!/usr/bin/env python3
"""Check clean export ordering, body fidelity and rejection of incomplete input."""
import tempfile
from pathlib import Path
import unittest
from build_complete_script import render


class CompleteScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.front = self.project / '前言.txt'
        self.front.write_text('剧名\n全剧概要\n概要内容。\n人物说明一览\nMio：人物。', encoding='utf-8')

    def episode(self, file_number, header_number):
        body = f'【{header_number}-1 日 内 房间·窗边】\n人物：Mio\n\n△（中景，固定）动作与空行保留。\nMio（轻声）：……待って。'
        source = f'剧名\n本集概要：只用于单集。\n【本集大场面】\n本集人物：Mio\n本集场景：房间\n【本集制作与演出约定】\n180秒\n第 {header_number} 集：标题\n（语言声明）\n\n{body}\n'
        (self.project / f'第{file_number}集.txt').write_text(source, encoding='utf-8')
        return body

    def test_numeric_order_and_verbatim_scene_bodies(self):
        bodies = {}
        for n in [10, 2, 8, 1, 7, 4, 6, 3, 5, 9]:
            bodies[n] = self.episode(n, n)
        content, files = render(self.project, self.front, 10)
        self.assertEqual(files[0].name, '第1集.txt')
        self.assertLess(content.index('第 2 集：'), content.index('第 10 集：'))
        self.assertTrue(content.startswith(self.front.read_text()))
        for body in bodies.values():
            self.assertIn(body, content)
        for removed in ['本集概要', '本集大场面', '本集制作与演出约定', '语言声明']:
            self.assertNotIn(removed, content)

    def test_missing_and_duplicate_episodes_are_rejected(self):
        self.episode(1, 1)
        self.episode(3, 3)
        with self.assertRaisesRegex(ValueError, '连续'):
            render(self.project, self.front, 3)
        self.episode('一', 1)
        with self.assertRaisesRegex(ValueError, '重复'):
            render(self.project, self.front)

    def test_header_mismatch_and_empty_body_are_rejected(self):
        self.episode('一', 2)
        with self.assertRaisesRegex(ValueError, '不符'):
            render(self.project, self.front)
        (self.project / '第一集.txt').write_text('第 1 集：标题\n没有场正文', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '场正文'):
            render(self.project, self.front)

    def test_chinese_episode_numbers_and_changed_source(self):
        self.episode('一', 1)
        second = self.episode('二', 2)
        before, _ = render(self.project, self.front, 2)
        f = self.project / '第二集.txt'
        f.write_text(f.read_text().replace('……待って。', 'もう大丈夫。'), encoding='utf-8')
        after, _ = render(self.project, self.front, 2)
        self.assertNotEqual(before, after)
        self.assertNotIn(second, after)
        self.assertIn('もう大丈夫。', after)


if __name__ == '__main__':
    unittest.main()
