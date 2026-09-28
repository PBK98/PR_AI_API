import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai import AuthenticationError, APIConnectionError

from ai_client import generate_commit, prepare_diff


class CommitTests(unittest.TestCase):
    def call(self, client):
        with patch('ai_client.load_dotenv'), patch.dict(os.environ, {'AI_API_KEY': 'fake-key'}), patch('ai_client.OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            result = generate_commit('+hello', 'gpt-5-mini', None, 2048, True)
            self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
            return result

    def test_success_and_single_request(self):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='chore: 테스트 파일 추가'))])
        self.assertEqual(self.call(client), 'chore: 테스트 파일 추가')
        client.chat.completions.create.assert_called_once()
        self.assertNotIn('temperature', client.chat.completions.create.call_args.kwargs)
        self.assertEqual(client.chat.completions.create.call_args.kwargs['max_completion_tokens'], 2048)

    def test_missing_key(self):
        with patch('ai_client.load_dotenv'), patch.dict(os.environ, {'AI_API_KEY': ''}), patch('ai_client.OpenAI') as factory:
            with self.assertRaisesRegex(RuntimeError, 'AI_API_KEY'):
                generate_commit('+hello', 'gpt-5-mini', None, 2048, True)
            factory.assert_not_called()

    def test_errors_do_not_leak_server_message(self):
        from unittest.mock import MagicMock
        request = httpx.Request('POST', 'https://copa.codyssey.kr/v1/chat/completions')
        errors = [
            AuthenticationError('SECRET', response=httpx.Response(401, request=request), body=None),
            APIConnectionError(message='SECRET', request=request),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                client = MagicMock()
                client.chat.completions.create.side_effect = error
                with self.assertRaises(RuntimeError) as caught:
                    self.call(client)
                self.assertNotIn('SECRET', str(caught.exception))

    def test_incomplete_response(self):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason='length', message=SimpleNamespace(content='partial'))])
        with self.assertRaisesRegex(RuntimeError, '완료되지'):
            self.call(client)

    def test_title_limit(self):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='feat: ' + '가' * 100))])
        self.assertLessEqual(len(self.call(client)), 72)

    def test_redaction_and_limit(self):
        diff = 'fake-key sk-example123\n' + 'x\n' * 300
        result = prepare_diff(diff, 'fake-key', True)
        self.assertNotIn('fake-key', result)
        self.assertNotIn('sk-example123', result)
        self.assertIn('나머지 diff 생략', result)
        self.assertLessEqual(len(result.splitlines()), 201)


if __name__ == '__main__':
    unittest.main()
