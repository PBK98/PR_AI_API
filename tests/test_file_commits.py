import contextlib
import io
import json
import unittest
from unittest.mock import patch

from app.ai_client import generate_file_commits
from app.git_client import collect_file_diffs
from app.cli import main


class FileCommitTests(unittest.TestCase):
    files = {'한글 file.py': '+hello', 'docs.md': '+world'}

    def generate(self, items):
        with patch('app.ai_client.request_text', return_value=json.dumps({'commits': items})) as request:
            result = generate_file_commits(self.files, 'gpt-5-mini', None, 2048, True)
            request.assert_called_once()
            return result

    def test_result_matched_by_id_not_order(self):
        result = self.generate([{'id': 1, 'title': 'docs: 설명 추가'}, {'id': 0, 'title': 'feat: 인사 추가'}])
        self.assertEqual(result['한글 file.py'], 'feat: 인사 추가')
        self.assertEqual(list(result), list(self.files))

    def test_missing_duplicate_unknown_and_empty_rejected(self):
        for items in ([], [{'id': 0, 'title': 'feat: 추가'}] * 2,
                      [{'id': 2, 'title': 'feat: 추가'}], [{'id': 0, 'title': ''}]):
            with self.subTest(items=items), self.assertRaises(RuntimeError):
                self.generate(items)

    def test_safe_limit_before_api(self):
        with patch('app.ai_client.request_text') as request, self.assertRaises(RuntimeError):
            generate_file_commits({str(i): '+x' for i in range(11)}, 'gpt-5-mini', None, 2048, True)
        request.assert_not_called()

    def test_safe_mode_preserves_each_file(self):
        files = {str(i): '+hello\n' * 500 for i in range(10)}
        reply = json.dumps({'commits': [{'id': i, 'title': 'feat: 추가'} for i in range(10)]})
        with patch('app.ai_client.request_text', return_value=reply) as request, contextlib.redirect_stdout(io.StringIO()):
            generate_file_commits(files, 'gpt-5-mini', None, 2048, True)
        records = json.loads(request.call_args.args[0])
        self.assertEqual(len(records), 10)
        self.assertTrue(all(len(record['diff'].splitlines()) <= 21 for record in records))

    def test_git_literal_paths(self):
        with patch('app.git_client.run_git', side_effect=['a b.py\0[abc].py\0', '+one', '+two']) as git:
            result = collect_file_diffs(True)
        self.assertEqual(result, {'a b.py': '+one', '[abc].py': '+two'})
        self.assertIn('--cached', git.call_args.args)
        self.assertEqual(git.call_args.args[-1], ':(literal)[abc].py')

    def test_cli_per_file(self):
        with patch('sys.argv', ['app', 'commit', '--per-file']), patch('app.cli.Path.exists', return_value=True), patch('app.cli.run_git', side_effect=['M file', 'unstaged', 'staged']), patch('app.cli.collect_file_diffs', return_value=self.files) as collect, patch('app.ai_client.generate_file_commits', return_value={'docs.md': 'docs: 설명 추가'}), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
        collect.assert_called_once_with(staged=True)
        self.assertIn('docs.md', output.getvalue())
        self.assertIn('docs: 설명 추가', output.getvalue())


if __name__ == '__main__':
    unittest.main()
