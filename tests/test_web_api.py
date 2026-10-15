import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import api
from fastapi.testclient import TestClient


def record():
    return SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15,
                           response_time=0.1, cost=0.001, model='test')


class WebApiTests(unittest.TestCase):
    def setUp(self):
        api.sessions.clear()
        self.client = TestClient(api.app)
        self.client.get('/api/session')

    def test_static_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="zh-CN">', response.text)

    def test_empty_question_rejected(self):
        response = self.client.post('/api/qa', json={'question':'  ', 'request_id':str(uuid4())})
        self.assertEqual(response.status_code, 422)

    def test_qa_once_and_feedback_ownership(self):
        store = Mock()
        store.search.return_value = [{'知识点id':'k1', '主题':'测试主题'}]
        actor = Mock(last_call=record(), last_conversation_id=101, last_monitor_error=None)
        actor.rag.return_value = '模型回答'
        payload = {'question':'测试问题', 'request_id':str(uuid4())}
        with patch.object(api, 'vector_store', return_value=store), \
             patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'RAGWithRecord', return_value=actor), \
             patch.object(api, 'save_feedback', return_value=1) as save:
            first = self.client.post('/api/qa', json=payload)
            self.assertEqual(first.status_code, 200)
            second = self.client.post('/api/qa', json=payload)
            self.assertEqual(first.json(), second.json())
            actor.rag.assert_called_once()
            self.assertEqual(self.client.post('/api/qa', json={**payload, 'question':'changed'}).status_code, 409)
            self.assertEqual(self.client.post('/api/feedback', json={'record_id':101,'score':1}).status_code, 200)
            self.assertEqual(self.client.post('/api/feedback', json={'record_id':101,'score':-1}).status_code, 200)
            self.assertEqual(save.call_count, 2)
            other = TestClient(api.app)
            other.get('/api/session')
            self.assertEqual(other.post('/api/feedback', json={'record_id':101,'score':1}).status_code, 403)

    def test_practice_uses_selected_topic_and_keeps_reference_server_side(self):
        actor = Mock(session_id=str(uuid4()), last_call=record(),
                     last_conversation_id=202, last_monitor_error=None)
        actor.ask.return_value = ('学生问题', None)
        result = {'reasoning':'测试', 'score':'good', 'missing_points':[], 'errors':[], 'suggestion':'举例'}
        actor.judge.return_value = (SimpleNamespace(model_dump=lambda:result), None)
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'PracticeWithRecord', return_value=actor):
            response = self.client.post('/api/practice/questions', json={
                'section':'连续分布', 'topic':'正态分布', 'request_id':str(uuid4())})
            self.assertEqual(response.status_code, 200)
            actor.ask.assert_called_once_with('连续分布','正态分布')
            self.assertNotIn('_knowledge', response.json())
            self.assertNotIn('prompt', response.json())
            eid = response.json()['exercise_id']
            payload = {'user_answer':'我的解释', 'request_id':str(uuid4())}
            judged = self.client.post(f'/api/practice/{eid}/judge', json=payload)
            self.assertEqual(judged.json()['evaluation'], result)
            self.client.post(f'/api/practice/{eid}/judge', json=payload)
            actor.judge.assert_called_once_with('我的解释')
            self.assertEqual(self.client.post(f'/api/practice/{uuid4()}/judge',json={
                **payload,'request_id':str(uuid4())}).status_code,409)

    def test_readonly_dashboard(self):
        response = self.client.get('/api/dashboard?limit=5')
        self.assertEqual(response.status_code,200)
        self.assertIn('stats',response.json())
        self.assertIn('feedback',response.json())
        self.assertLessEqual(len(response.json()['records']),5)

    def test_invalid_feedback(self):
        self.assertEqual(self.client.post('/api/feedback',json={'record_id':1,'score':0}).status_code,422)


if __name__ == '__main__':
    unittest.main()
