import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.ai_client import generate_pr
from app.pr_template import load_template, render_template, template_slots, validate_sections

TEMPLATE = Path('.github/pull_request_template.md').read_text()


def reply():
    return json.dumps({'title': 'feat: 템플릿 지원', 'fields': {
        str(index): '확인할 변경 사항' for index in template_slots(TEMPLATE)
    }})


class TemplateTests(unittest.TestCase):
    def test_headers_and_fixed_checklists_preserved(self):
        title, body = render_template(reply(), TEMPLATE)
        self.assertEqual(title, 'feat: 템플릿 지원')
        slots = template_slots(TEMPLATE)
        for index, line in enumerate(TEMPLATE.splitlines()):
            if index not in slots:
                self.assertEqual(body.splitlines()[index], line)
        self.assertIn('- **작업자**: 확인 필요', body)
        self.assertNotIn('[x]', body)

    def test_generated_checkbox_cannot_mark_item_complete(self):
        data = json.loads(reply())
        for key in data['fields']:
            data['fields'][key] = '- [x] 완료\n## 새 섹션'
        _, body = render_template(json.dumps(data), TEMPLATE)
        self.assertNotIn('[x]', body)
        self.assertNotIn('\n## 새 섹션', body)

    def test_missing_extra_empty_and_malformed_rejected(self):
        for text in ('invalid', '{}', json.dumps({'title': 'title', 'fields': {}})):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                render_template(text, TEMPLATE)
        for value in ('', '- [ ]'):
            data = json.loads(reply())
            data['fields'][next(iter(data['fields']))] = value
            with self.assertRaises(RuntimeError):
                render_template(json.dumps(data), TEMPLATE)

    def test_generate_uses_template_once(self):
        with patch('app.ai_client.load_template', return_value=TEMPLATE), patch('app.ai_client.request_text', return_value=reply()) as request:
            title, body = generate_pr('+example', 'gpt-5-mini', None, 2048, True)
        request.assert_called_once()
        self.assertIn(TEMPLATE, request.call_args.args[-1])
        self.assertIn('## 📌 PR 개요', body)
        self.assertIn('## Why', body)
        self.assertIn('## What', body)
        self.assertIn('## How to Test', body)

    def test_required_sections_rejected_if_missing(self):
        for header in ('Why', 'What', 'How to Test'):
            with self.subTest(header=header), self.assertRaises(RuntimeError):
                validate_sections(TEMPLATE.replace('## ' + header, '## Other'))

    def test_missing_and_empty_template(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'template.md')
            with patch('app.pr_template.TEMPLATE_PATH', path):
                self.assertIsNone(load_template())
                path.write_text('  ')
                with self.assertRaises(RuntimeError):
                    load_template()


if __name__ == '__main__':
    unittest.main()
