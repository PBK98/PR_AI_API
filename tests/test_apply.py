import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.cli import confirm_commit, main


class ApplyTests(unittest.TestCase):
    def test_cancel(self):
        for answer in ('', 'n', 'yes'):
            with self.subTest(answer=answer), patch('builtins.input', return_value=answer), patch('app.cli.run_git') as git, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(confirm_commit('feat: test', 'snapshot'), 0)
                git.assert_not_called()

    def test_input_interrupted(self):
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error), patch('builtins.input', side_effect=error), patch('app.cli.run_git') as git, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(confirm_commit('feat: test', 'snapshot'), 0)
                git.assert_not_called()

    def test_changed_index(self):
        with patch('builtins.input', return_value='y'), patch('app.cli.run_git', return_value='changed') as git, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(confirm_commit('feat: test', 'snapshot'), 1)
            self.assertEqual(git.call_count, 1)

    def test_requires_staging_before_api(self):
        with patch('sys.argv', ['app', 'commit', '--apply']), patch('app.cli.Path.exists', return_value=True), patch('app.cli.run_git', side_effect=[' M file', 'diff', '']), patch('app.ai_client.generate_commit') as generate, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)
            generate.assert_not_called()

    def test_invalid_option_combinations(self):
        for argv in (['--apply'], ['pr', '--apply']):
            with self.subTest(argv=argv), patch('sys.argv', ['app', *argv]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)

    def test_real_commit_contains_only_staged_content(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=directory, text=True)
            git('init', '--quiet')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'commit.gpgsign', 'false')
            git('config', 'core.hooksPath', directory + '/no-hooks')
            path = Path(directory, 'file.txt')
            path.write_text('staged\n')
            git('add', 'file.txt')
            path.write_text('unstaged\n')
            snapshot = git('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv')
            # 임시 저장소에서 실제 커밋을 검증한다.
            def run(*args):
                return git(*args)
            with patch('app.cli.run_git', side_effect=run), patch('builtins.input', return_value='y'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(confirm_commit('test: staged content', snapshot), 0)
            self.assertEqual(git('show', 'HEAD:file.txt'), 'staged\n')
            self.assertEqual(path.read_text(), 'unstaged\n')
            self.assertEqual(git('log', '-1', '--format=%s').strip(), 'test: staged content')


if __name__ == '__main__':
    unittest.main()
