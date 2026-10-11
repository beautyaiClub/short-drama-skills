"""Regression checks for voice classification and dialogue extraction."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

audit = module('audit', ROOT / 'short-drama-script-audit/scripts/audit_plain_script.py')
builder = module('builder', ROOT / 'short-drama-script/scripts/build_derived_docs.py')

class VoiceTests(unittest.TestCase):
    def test_ordinary_dialogue_and_device_names_do_not_require_voice_tags(self):
        for cue in ['挽着周砚舟，笑着抱怨', '无线电，平', '没有回答喇叭', '从门外传来，急促']:
            self.assertEqual(audit.voice_findings(cue, ''), [])

    def test_explicit_os_and_vo_are_valid(self):
        for cue, tag in [('画外对白，从门外喊', 'OS'), ('内心独白，发懵', 'VO'), ('回忆旁白，平静', 'VO')]:
            self.assertEqual(audit.voice_findings(cue, tag), [])

    def test_swapped_or_missing_types_fail(self):
        for cue, tag in [('内心独白，平', 'OS'), ('画外对白，从门外喊', 'VO'), ('内心独白，平', '')]:
            self.assertTrue(any(item[0] == 'FAIL' for item in audit.voice_findings(cue, tag)))

    def test_bare_tags_and_legacy_os_require_clarification(self):
        for cue, tag in [('平', 'VO'), ('平', 'OS'), ('OS，发懵', '')]:
            self.assertTrue(audit.voice_findings(cue, tag))

    def test_both_voice_kinds_remain_dialogue_and_derived_labels(self):
        text = '''示例 · DEMO
本集概要：声音分类示例。
【本集大场面】
· 现场与独白。
本集人物：阿棠、苏见微
本集场景：沈府·耳房
第 1 集：声音
(人物中文 · 台词中文)
【1-1 日 内 沈府·耳房】
人物：阿棠、苏见微
阿棠（画外对白，从门外喊，急促）[OS]：小姐！
苏见微（内心独白，平）[VO]：我要先看看。
苏见微（平）：进来吧。
'''
        scenes = audit.split_scenes(text, 1)
        self.assertEqual([d['voice'] for d in scenes[0]['dlg']], ['OS', 'VO', ''])
        self.assertEqual(len(scenes[0]['dlg']), 3)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            script = project / '第一集.txt'
            script.write_text(text)
            cn_map = {(1, d['text']): d['text'] for d in scenes[0]['dlg']}
            lines, missing = builder.rebuild_reference('示例', 'DEMO', [(1, script)], project, cn_map, False)
            self.assertEqual(missing, [])
            sheet = '\n'.join(lines)
            self.assertIn('阿棠（画外对白，从门外喊，急促）[OS]', sheet)
            self.assertIn('苏见微（内心独白，平）[VO]', sheet)
            self.assertEqual(sheet.count('EN｜') - 1, 3)

if __name__ == '__main__':
    unittest.main()
