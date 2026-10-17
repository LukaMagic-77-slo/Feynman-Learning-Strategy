import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'monitoring'), str(ROOT)]
from assistant import AgentWithRecord


class Item(SimpleNamespace):
    def model_dump(self, **kwargs):
        return vars(self)


def response(items, text='', tokens=15):
    return SimpleNamespace(output=items, output_text=text, usage=SimpleNamespace(
        input_tokens=tokens - 5, output_tokens=5, total_tokens=tokens))


class AgentMonitorTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'DASHSCOPE_MODEL': 'test-model'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = Mock()
        self.store = Mock()
        self.store.search.return_value = []
        index_patch = patch('agent.tools.get_index', return_value=self.store)
        index_patch.start()
        self.addCleanup(index_patch.stop)
        self.call = Item(type='function_call', name='search',
                         arguments='{"query":"密度"}', call_id='call1')
        self.message = Item(type='message', content=[SimpleNamespace(text='答案')])

    def responses(self):
        return [response([self.call]), response([self.message], '答案', 25)]

    def test_each_response_saved_and_usage_not_duplicated(self):
        self.client.responses.create.side_effect = self.responses()
        self.store.search.return_value = [{'知识点id': 'k1', '主题': '密度'}]
        search = self.store.search
        actor = AgentWithRecord(self.client)
        saved = []

        def persist(record, question, course):
            saved.append(record)
            record.id = 100 + len(saved)
            return record.id, None

        with patch('assistant.persist_record', side_effect=persist):
            self.assertEqual(actor.rag('为什么'), '答案')
        self.assertEqual(len(saved), 2)
        self.assertEqual([r.total_tokens for r in saved], [15, 25])
        self.assertEqual(actor.last_call.total_tokens, 40)
        self.assertEqual(actor.last_conversation_id, 102)
        self.assertTrue(all(r.session_id == actor.session_id for r in saved))
        self.assertTrue(all(r.question == '为什么' for r in saved))
        self.assertIn('function_call_output', saved[1].prompt)
        self.assertNotIn('function_call_output', saved[0].prompt)
        search.assert_called_once_with('密度')

    def test_next_query_does_not_resave_old_records(self):
        self.client.responses.create.side_effect = self.responses() + self.responses()
        actor = AgentWithRecord(self.client)
        runs = []

        def persist(record, question, course):
            record.id = len(runs) + 1
            runs.append(record.session_id)
            return record.id, None

        with patch('assistant.persist_record', side_effect=persist):
            actor.rag('第一题')
            actor.rag('第二题')
        self.assertEqual(len(runs), 4)
        self.assertEqual(len(actor.call_record), 2)
        self.assertNotEqual(runs[0], runs[2])

    def test_save_failure_preserves_answer_and_other_records(self):
        self.client.responses.create.side_effect = self.responses()
        actor = AgentWithRecord(self.client)

        def persist(record, question, course):
            if not record.answer:
                record.id = 101
                return 101, None
            return None, 'simulated database failure'

        with patch('assistant.persist_record', side_effect=persist) as save:
            self.assertEqual(actor.rag('问题'), '答案')
        self.assertEqual(save.call_count, 2)
        self.assertIsNone(actor.last_conversation_id)
        self.assertIsNotNone(actor.last_monitor_error)

    def test_tool_failure_still_saves_completed_model_call(self):
        self.client.responses.create.return_value = response([self.call])
        self.store.search.side_effect = RuntimeError('search failed')
        actor = AgentWithRecord(self.client)
        with patch('assistant.persist_record', return_value=(101, None)) as save:
            with self.assertRaisesRegex(RuntimeError, 'search failed'):
                actor.rag('问题')
        self.assertEqual(save.call_count, 1)
        self.assertIsNone(actor.last_conversation_id)

    def test_api_writes_one_insert_per_response(self):
        import api
        import save_record
        from fastapi.testclient import TestClient
        from uuid import uuid4

        self.client.responses.create.side_effect = self.responses()
        inserted = []
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        cursor.execute.side_effect = lambda sql, args: inserted.append((sql, args))
        cursor.fetchone.side_effect = lambda: (100 + len(inserted),)
        conn = Mock()
        conn.cursor.return_value = cursor
        self.store.search.return_value = [{'知识点id': 'k1', '主题': '密度'}]
        api.sessions.clear()

        with patch.object(api, 'model_client', return_value=self.client), \
             patch.object(save_record, 'get_db_connection', return_value=conn):
            with TestClient(api.app) as browser:
                browser.get('/api/session')
                payload = {'question': '为什么', 'request_id': str(uuid4())}
                result = browser.post('/api/qa', json=payload)
                self.assertEqual(result.status_code, 200)
                data = result.json()
                self.assertEqual(data['record_id'], 102)
                self.assertEqual(data['usage']['total_tokens'], 40)
                self.assertEqual(data['sources'], [])
                self.assertEqual(browser.post('/api/qa', json=payload).json(), data)

        self.assertEqual(len(inserted), 2)
        self.assertTrue(all('INSERT INTO conversations' in sql for sql, _ in inserted))
        self.assertEqual([args[8] for _, args in inserted], [15, 25])
        self.assertEqual(inserted[0][1][13], inserted[1][1][13])
        self.assertEqual(conn.commit.call_count, 2)

    def test_monitor_uses_original_registry_for_any_tool(self):
        from agent.register_tools import tool_handlers, tool_list
        custom = Mock(return_value={'value': 42})
        call = Item(type='function_call', name='custom_tool', arguments='{}', call_id='custom1')
        self.client.responses.create.side_effect = [response([call]), response([self.message], '答案')]
        with patch.dict(tool_handlers, {'custom_tool': custom}), \
             patch('assistant.persist_record', return_value=(101, None)) as save:
            actor = AgentWithRecord(self.client)
            self.assertIs(actor.tool_handlers, tool_handlers)
            self.assertIs(actor.tool_list, tool_list)
            self.assertEqual(actor.rag('问题'), '答案')
            custom.assert_called_once_with()
            self.assertEqual(save.call_count, 2)
        self.store.search.assert_not_called()


if __name__ == '__main__':
    unittest.main()
