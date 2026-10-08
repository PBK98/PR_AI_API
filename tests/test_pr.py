import contextlib
import io
import json
import unittest
from unittest.mock import patch

from ai_client import PR_INSTRUCTIONS, format_pr, generate_pr
from main import main


def response(**overrides):
    data = dict(title='feat: PR 초안 생성', why=['변경 배경 확인 필요'],
                what=['PR 초안 생성 명령 추가'], how_to_test=['제안(미실행): 출력 확인'])
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


class PRTests(unittest.TestCase):
    def test_valid_sections(self):
        title, body = format_pr(response())
        self.assertEqual(title, 'feat: PR 초안 생성')
        for header in ('Why', 'What', 'How to Test'):
            self.assertIn(f'## {header}\n- ', body)

    def test_title_and_bullet_normalization(self):
        title, body = format_pr(response(title='가' * 100 + '\n나', what=['첫 줄\n두 번째 줄']))
        self.assertLessEqual(len(title), 80)
        self.assertNotIn('\n', title)
        self.assertIn('- 첫 줄 두 번째 줄', body)

    def test_bad_response_rejected(self):
        for text in ('not json', '[]', response(title=''), response(why=[]),
                     response(what='text'), response(how_to_test=['']), response(why=['-'])):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                format_pr(text)

    def test_fenced_json(self):
        self.assertEqual(format_pr('```json\n' + response() + '\n```'), format_pr(response()))

    def test_shared_request_once(self):
        with patch('ai_client.request_text', return_value=response()) as request:
            generate_pr('+hello', 'gpt-5-mini', None, 2048, True)
            request.assert_called_once_with('+hello', 'gpt-5-mini', None, 2048, True, PR_INSTRUCTIONS)

    def test_cli_staged_diff_and_output(self):
        with patch('sys.argv', ['main.py', 'pr', '--safe-mode']), patch('main.Path.exists', return_value=True), patch('main.run_git', side_effect=['M file', 'unstaged', 'staged']), patch('ai_client.generate_pr', return_value=format_pr(response())) as generate, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
            self.assertEqual(generate.call_args.args[0], 'staged')
            self.assertIn('--- PR Title ---', output.getvalue())
            self.assertIn('--- PR Body ---', output.getvalue())

    def test_cli_no_diff_does_not_call_api(self):
        for results in ([''], ['?? new', '', '']):
            with self.subTest(results=results), patch('sys.argv', ['main.py', 'pr']), patch('main.Path.exists', return_value=True), patch('main.run_git', side_effect=results), patch('ai_client.generate_pr') as generate, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
                generate.assert_not_called()

    def test_cli_invalid_response_returns_error(self):
        with patch('sys.argv', ['main.py', 'pr']), patch('main.Path.exists', return_value=True), patch('main.run_git', side_effect=['M file', 'diff', '']), patch('ai_client.generate_pr', side_effect=RuntimeError('PR 형식 오류')), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(main(), 1)
            self.assertIn('PR 형식 오류', error.getvalue())


if __name__ == '__main__':
    unittest.main()
