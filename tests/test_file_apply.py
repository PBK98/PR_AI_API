import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.cli import confirm_file_commits
from app.git_client import commit_staged_file, run_git


class FileApplyTests(unittest.TestCase):
    def test_real_separate_commits_preserve_unstaged_changes(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                run_git('init', '--quiet')
                run_git('config', 'user.name', 'Test')
                run_git('config', 'user.email', 'test@example.invalid')
                run_git('config', 'commit.gpgsign', 'false')
                run_git('config', 'core.hooksPath', directory + '/hooks-disabled')
                Path('a space.txt').write_text('staged a\n')
                Path('[b].bin').write_bytes(b'\x00\x01\x02')
                run_git('add', '--', 'a space.txt', '[b].bin')
                Path('a space.txt').write_text('unstaged a\n')
                snapshot = run_git('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv')
                with patch('builtins.input', return_value='y'), contextlib.redirect_stdout(io.StringIO()):
                    result = confirm_file_commits({'a space.txt': 'feat: a 추가', '[b].bin': 'feat: b 추가'}, snapshot)
                self.assertEqual(result, 0)
                self.assertEqual(run_git('rev-list', '--count', 'HEAD').strip(), '2')
                self.assertEqual(run_git('show', 'HEAD:a space.txt'), 'staged a\n')
                self.assertEqual(Path('a space.txt').read_text(), 'unstaged a\n')
                self.assertEqual(run_git('diff', '--cached'), '')
                self.assertEqual(run_git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').strip(), '[b].bin')
                # 기존 파일 삭제도 단독 커밋하며 다른 파일 수정은 스테이징에 남긴다.
                Path('[b].bin').unlink()
                run_git('add', '--', '[b].bin', 'a space.txt')
                commit_staged_file('[b].bin', 'chore: b 삭제')
                self.assertEqual(run_git('diff', '--cached', '--name-only').strip(), 'a space.txt')
                self.assertEqual(run_git('show', 'HEAD:a space.txt'), 'staged a\n')
            finally:
                os.chdir(previous)

    def test_cancel_does_not_commit(self):
        with patch('builtins.input', return_value='n'), patch('app.cli.commit_staged_file') as commit, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(confirm_file_commits({'a': 'feat: a'}, 'snapshot'), 0)
            commit.assert_not_called()

    def test_failure_stops_after_completed_commits(self):
        with patch('builtins.input', return_value='y'), patch('app.cli.run_git', side_effect=['snapshot', 'a patch', 'b patch', 'a patch', 'b patch']), patch('app.cli.commit_staged_file', side_effect=['committed\n', RuntimeError('hook failed')]) as commit, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(confirm_file_commits({'a': 'feat: a', 'b': 'feat: b'}, 'snapshot'), 1)
            self.assertEqual(commit.call_count, 2)
            self.assertIn('완료 1/2', error.getvalue())


if __name__ == '__main__':
    unittest.main()
