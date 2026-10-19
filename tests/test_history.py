import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'monitoring'), str(ROOT)]
import api
import record_query
import save_history
from call_record import LLMCallRecord
from fastapi.testclient import TestClient


class HistoryTests(unittest.TestCase):
    def setUp(self):
        api.sessions.clear()
        self.browser = TestClient(api.app)
        self.browser.get('/api/session')

    def actor(self):
        record = LLMCallRecord('test', 'prompt', 'instructions', '答案', 10, 5, 15, .1, 0)
        return Mock(last_call=record, last_conversation_id=101,
                    last_monitor_error=None, session_id=str(uuid4()),
                    rag=Mock(return_value='答案'))

    def test_save_final_history_once_with_chat_id(self):
        actor = self.actor()
        chat_id = str(uuid4())
        payload = {'question': '第一条问题', 'chat_id': chat_id, 'request_id': str(uuid4())}
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'create_assistant', return_value=actor), \
             patch.object(api, 'get_history', return_value=[]), \
             patch.object(api, 'save_history', return_value=7) as save:
            first = self.browser.post('/api/qa', json=payload)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()['chat_id'], chat_id)
            self.assertEqual(first.json()['history_id'], 7)
            self.assertEqual(self.browser.post('/api/qa', json=payload).json(), first.json())
        save.assert_called_once()
        saved = save.call_args.args[0]
        self.assertEqual(saved.chat_id, chat_id)
        self.assertEqual(saved.session_id, actor.session_id)
        self.assertEqual(saved.answer, '答案')
        self.assertIsNone(actor.last_call.chat_id)
        actor.rag.assert_called_once_with('第一条问题', history=[])

    def test_history_failure_does_not_hide_answer(self):
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'create_assistant', return_value=self.actor()), \
             patch.object(api, 'get_history', return_value=[]), \
             patch.object(api, 'save_history', side_effect=RuntimeError('test failure')), \
             patch.object(api.log, 'exception'):
            response = self.browser.post('/api/qa', json={
                'question': '问题', 'chat_id': str(uuid4()), 'request_id': str(uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], '答案')
        self.assertIsNotNone(response.json()['history_warning'])

    def test_same_chat_context_is_loaded_before_current_turn_is_saved(self):
        actor = self.actor()
        chat_id = str(uuid4())
        rows = [
            {'question': '什么是指数分布？', 'answer': '它描述等待时间。'},
            {'question': '它的参数是什么？', 'answer': '率参数λ。'},
        ]
        events = []
        def load(**kwargs):
            self.assertEqual(kwargs, {'limit': None, 'chat_id': chat_id})
            events.append('load')
            return rows
        def run(query, history):
            events.append('agent')
            self.assertEqual(query, '那均值呢？')
            self.assertEqual(history, [
                {'role':'user','content':'什么是指数分布？'},
                {'role':'assistant','content':'它描述等待时间。'},
                {'role':'user','content':'它的参数是什么？'},
                {'role':'assistant','content':'率参数λ。'},
            ])
            return '答案'
        actor.rag.side_effect = run
        def save(*args, **kwargs):
            events.append('save')
            return 9
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'create_assistant', return_value=actor), \
             patch.object(api, 'get_history', side_effect=load) as get, \
             patch.object(api, 'save_history', side_effect=save):
            payload = {'question':'那均值呢？','chat_id':chat_id,'request_id':str(uuid4())}
            response = self.browser.post('/api/qa', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.browser.post('/api/qa', json=payload).json(), response.json())
            get.assert_called_once()
        self.assertEqual(events, ['load','agent','save'])

    def test_question_without_chat_id_does_not_load_other_chat_history(self):
        actor = self.actor()
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'create_assistant', return_value=actor), \
             patch.object(api, 'get_history') as load, \
             patch.object(api, 'save_history') as save:
            response = self.browser.post('/api/qa', json={'question':'问题','request_id':str(uuid4())})
        self.assertEqual(response.status_code, 200)
        actor.rag.assert_called_once_with('问题')
        load.assert_not_called()
        save.assert_not_called()

    def test_list_and_load_history_without_model_calls(self):
        chat_id = str(uuid4())
        turns = [{'id': 1, 'question': '第一题', 'answer': '回答', 'record_id': 101}]
        with patch.object(api, 'get_chat_list', return_value=[{'chat_id': chat_id, 'title': '第一题'}]), \
             patch.object(api, 'get_history', return_value=turns) as load, \
             patch.object(api, 'model_client') as model:
            self.assertEqual(self.browser.get('/api/chats').json()[0]['title'], '第一题')
            self.assertEqual(self.browser.get(f'/api/chats/{chat_id}/history').json(), turns)
            load.assert_called_once_with(limit=None, chat_id=chat_id)
            model.assert_not_called()
        with patch.object(api, 'save_feedback', return_value=9):
            self.assertEqual(self.browser.post('/api/feedback', json={'record_id':101,'score':1}).status_code, 200)

    def test_invalid_chat_id_rejected(self):
        self.assertEqual(self.browser.get('/api/chats/not-a-uuid/history').status_code, 422)

    def test_history_sql_filters_and_orders(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [(1,'q','a','概率论','qa_answer','chat','run',None,
                                        datetime.now(timezone.utc),101,None)]
        with patch.object(record_query, 'get_db_connection', return_value=conn):
            rows = record_query.get_history(limit=None, chat_id='chat')
        sql, params = cursor.execute.call_args.args
        self.assertIn('WHERE chat_id = %s', sql)
        self.assertIn('ORDER BY id ASC', sql)
        self.assertEqual(params, ('chat',))
        self.assertEqual(rows[0]['record_id'], 101)

    def test_save_history_uses_bound_parameters(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (7,)
        record = self.actor().last_call
        record.chat_id = str(uuid4())
        with patch.object(save_history, 'get_db_connection', return_value=conn):
            result = save_history.save_history(record, '问题', '概率论', conversation_id=101)
        self.assertEqual(result, 7)
        sql, values = cursor.execute.call_args.args
        self.assertIn('INSERT INTO chat_history', sql)
        self.assertEqual(values[4], record.chat_id)
        self.assertEqual(values[8], 101)
        conn.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
