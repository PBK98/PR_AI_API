import argparse
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from app.cli import apply_pr
from app.github_client import PRPlan, prepare_pr, publish_pr


PLAN = PRPlan('owner/repo', 'https://github.com/owner/repo.git', 'feature/test', 'main', 'abc123', '+hello')


class GithubTests(unittest.TestCase):
    def state(self, *args):
        return {
            ('branch', '--show-current'): PLAN.branch,
            ('rev-parse', 'HEAD'): PLAN.head,
            ('status', '--porcelain'): '',
            ('remote', 'get-url', '--push', 'origin'): PLAN.remote_url,
        }.get(args, '')

    def test_publish_push_before_create_and_exact_body(self):
        calls = []
        body = '## Why\n- 이유\n\n## What\n- 변경\n\n## How to Test\n- 확인'
        def git(*args):
            calls.append(args)
            return self.state(*args)
        def gh(*args):
            self.assertEqual(calls[-1], ('push', PLAN.remote_url, 'abc123:refs/heads/feature/test'))
            self.assertEqual(Path(args[-1]).read_text(), body)
            self.assertIn('--head', args)
            return 'https://github.com/owner/repo/pull/1\n'
        with patch('app.github_client.run_git', side_effect=git), patch('app.github_client.existing_pr', return_value=None), patch('app.github_client.run_gh', side_effect=gh):
            self.assertTrue(publish_pr(PLAN, 'feat: test', body).endswith('/1'))

    def test_push_failure_does_not_create(self):
        def git(*args):
            if args[0] == 'push':
                raise RuntimeError('push rejected')
            return self.state(*args)
        with patch('app.github_client.run_git', side_effect=git), patch('app.github_client.existing_pr', return_value=None), patch('app.github_client.run_gh') as gh, self.assertRaisesRegex(RuntimeError, 'push rejected'):
            publish_pr(PLAN, 'title', 'body')
        gh.assert_not_called()

    def test_changed_state_does_not_push(self):
        with patch('app.github_client.run_git', return_value='other') as git, self.assertRaisesRegex(RuntimeError, '바뀌었습니다'):
            publish_pr(PLAN, 'title', 'body')
        self.assertFalse(any(call.args[0] == 'push' for call in git.call_args_list))

    def test_duplicate_does_not_push(self):
        with patch('app.github_client.run_git', side_effect=self.state) as git, patch('app.github_client.existing_pr', return_value='https://github.com/owner/repo/pull/1'), self.assertRaisesRegex(RuntimeError, '이미 열린'):
            publish_pr(PLAN, 'title', 'body')
        self.assertFalse(any(call.args[0] == 'push' for call in git.call_args_list))

    def test_create_failure_reports_pushed_branch(self):
        with patch('app.github_client.run_git', side_effect=self.state), patch('app.github_client.existing_pr', return_value=None), patch('app.github_client.run_gh', side_effect=RuntimeError('network')), self.assertRaisesRegex(RuntimeError, '브랜치는 push됐지만'):
            publish_pr(PLAN, 'title', 'body')

    def test_prepare_uses_committed_branch_diff(self):
        def git(*args):
            if args == ('rev-parse', 'FETCH_HEAD'):
                return 'base123'
            if args[0] == 'diff':
                self.assertIn('base123...abc123', args)
                return '+hello'
            return self.state(*args)
        with patch('app.github_client.run_git', side_effect=git), patch('app.github_client.run_gh', return_value='{"defaultBranchRef":{"name":"main"}}'), patch('app.github_client.existing_pr', return_value=None):
            self.assertEqual(prepare_pr(None), PLAN)

    def test_dirty_repository_rejected_before_github(self):
        with patch('app.github_client.run_git', return_value=' M file'), patch('app.github_client.run_gh') as gh, self.assertRaisesRegex(RuntimeError, '커밋하거나'):
            prepare_pr(None)
        gh.assert_not_called()

    def test_default_branch_rejected(self):
        def git(*args):
            return 'main' if args == ('branch', '--show-current') else self.state(*args)
        with patch('app.github_client.run_git', side_effect=git), patch('app.github_client.run_gh', return_value='{"defaultBranchRef":{"name":"main"}}'), self.assertRaisesRegex(RuntimeError, '작업 브랜치'):
            prepare_pr(None)

    def test_cancel_no_publication(self):
        args = argparse.Namespace(base=None, model='gpt-5-mini', temperature=None, max_tokens=2048, safe_mode=True)
        with patch('app.github_client.prepare_pr', return_value=PLAN), patch('app.ai_client.generate_pr', return_value=('title', 'body')), patch('builtins.input', return_value='n'), patch('app.github_client.publish_pr') as publish, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(apply_pr(args), 0)
        publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
