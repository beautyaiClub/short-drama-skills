"""Regression coverage for explicit integrated-format selection and invariants."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


audit = load('director_audit', ROOT / 'short-drama-script-audit/scripts/audit_plain_script.py')
builder = load('director_builder', ROOT / 'short-drama-script/scripts/build_derived_docs.py')
timing = load('director_timing', ROOT / 'short-drama-script/scripts/estimate_duration.py')

SCRIPT = '''示例 · DEMO
本集概要：Mio检查连接。
【本集大场面】
· 连接确认。
本集人物：Mio
本集场景：站台·外沿
第 1 集：接应
（人物标识拉丁字母 · 台词日语）
【1-1 日 外 站台·外沿】
人物：Mio
△（近景，固定机位）Mio检查连接，镜头保留锁门，手指压住锁扣。
Mio（吸气短停，目光落在锁门，声音压低）：まだ。掛かってない。
'''


class DirectorFormatTests(unittest.TestCase):
    def check_script(self, text=SCRIPT, mode='director-integrated'):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '第一集.txt'
            path.write_text(text, encoding='utf-8')
            findings = []
            audit.check_episode(1, path, {'站台': {'外沿'}}, {'Mio'}, set(), True,
                                findings, {'script_format': mode, 'spec_seconds': 210})
            return findings

    def test_default_is_plain_and_mentions_do_not_select_integrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            self.assertEqual(audit.read_script_format(p), 'plain')
            f = p / '示例-全局设定.txt'
            f.write_text('备注：不采用导演执行整合稿。\n', encoding='utf-8')
            self.assertEqual(audit.read_script_format(p), 'plain')
            f.write_text('剧本格式：导演执行整合稿\n', encoding='utf-8')
            self.assertEqual(audit.read_script_format(p), 'director-integrated')
            self.assertTrue(timing.is_integrated(p / '第一集.txt'))
            f.write_text('剧本格式：纯场次本\n', encoding='utf-8')
            self.assertEqual(audit.read_script_format(p), 'plain')
            self.assertFalse(timing.is_integrated(p / '第一集.txt'))

    def test_camera_allowed_only_in_declared_mode_and_timing_not_falsely_fitted(self):
        integrated = self.check_script()
        self.assertFalse(any(f['level'] == 'FAIL' for f in integrated))
        self.assertFalse(any(f['kind'] in ('篇幅偏长', '篇幅偏短') for f in integrated))
        plain = self.check_script(mode='plain')
        self.assertTrue(any(f['kind'] == '旧格式字段' for f in plain))
        self.assertTrue(any(f['kind'] == '篇幅偏短' for f in plain))

    def test_voice_and_speaker_checks_remain_active(self):
        bad_voice = SCRIPT.replace('Mio（吸气短停，目光落在锁门，声音压低）：',
                                   'Mio（内心独白，气息压低）[OS]：')
        self.assertTrue(any(f['level'] == 'FAIL' and 'OS' in f['kind']
                            for f in self.check_script(bad_voice)))
        missing_actor = SCRIPT.replace('人物：Mio\n', '人物：Ren\n')
        self.assertTrue(any(f['kind'] == '说话人不在人物行'
                            for f in self.check_script(missing_actor)))

    def test_performance_cue_and_japanese_survive_derived_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            script = p / '第一集.txt'
            script.write_text(SCRIPT, encoding='utf-8')
            jp = 'まだ。掛かってない。'
            text, missing = builder.rebuild_reference('示例', 'DEMO', [(1, script)], p,
                                                      {(1, jp): '还没扣好。'}, False)
            self.assertEqual(missing, [])
            self.assertIn('Mio（吸气短停，目光落在锁门，声音压低）', '\n'.join(text))
            self.assertIn('EN｜' + jp, '\n'.join(text))


if __name__ == '__main__':
    unittest.main()
