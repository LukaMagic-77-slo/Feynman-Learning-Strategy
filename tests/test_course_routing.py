import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import api


def call_record():
    return SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15,
                           response_time=0.1, cost=0.001, model='test')


class CourseRoutingTests(unittest.TestCase):
    def test_calculus_qa_uses_calculus_agent(self):
        actor = Mock(last_call=call_record(), last_conversation_id=None, last_monitor_error=None)
        actor.rag.return_value = '高数回答'
        body = api.Question(question='什么是一致连续？', course='高等数学', request_id=uuid4())
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'create_assistant', return_value=actor) as factory:
            response = api.qa(body, api.BrowserSession('test'))
        self.assertEqual(response['course'], '高等数学')
        self.assertEqual(factory.call_args.kwargs['course'], '高等数学')

    def test_calculus_practice_uses_calculus_course(self):
        actor = Mock(session_id=str(uuid4()), last_call=call_record(),
                     last_conversation_id=None, last_monitor_error=None)
        actor.ask.return_value = ('高数学生问题', None)
        body = api.PracticeQuestion(section='函数与极限', topic='第一节：映射与函数',
                                    course='高等数学', request_id=uuid4())
        with patch.object(api, 'model_client', return_value=Mock()), \
             patch.object(api, 'PracticeWithRecord', return_value=actor) as factory:
            response = api.practice_question(body, api.BrowserSession('test'))
        self.assertEqual(response['course'], '高等数学')
        self.assertEqual(factory.call_args.kwargs['course'], '高等数学')
        actor.ask.assert_called_once_with('函数与极限', '第一节：映射与函数')


if __name__ == '__main__':
    unittest.main()
