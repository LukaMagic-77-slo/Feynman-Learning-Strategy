import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'monitoring'), str(ROOT / 'evaluation'), str(ROOT)]
from practice_record import PracticeWithRecord


class TopicSelectionTests(unittest.TestCase):
    def setUp(self):
        self.usage = SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2)
        self.documents = [{'课程':'概率论', '章节':'连续分布', '主题':'正态分布',
                           '知识点内容':'normal', '知识点id':'n1', '关键词':['normal']}]
        self.exercise = PracticeWithRecord(Mock())

    @patch.dict(os.environ, {'DASHSCOPE_MODEL':'qwen3.8-flash'})
    def test_selected_topic_only_and_judge_snapshot(self):
        with patch('practice.get_knowledge.get_knowledge', return_value=self.documents) as query, \
             patch('practice.practice.feynman', return_value=('question', self.usage)) as ask, \
             patch('practice_record.persist_record', return_value=(1, None)), \
             patch('practice.judge.judge_answer') as judge:
            self.exercise.ask('连续分布', '正态分布')
            query.assert_called_once_with('概率论', '连续分布', '正态分布')
            self.assertEqual(ask.call_args.args[2], self.documents)
            self.documents[0]['主题'] = '指数分布'
            self.documents[0]['知识点内容'] = 'changed'
            judge.return_value = (SimpleNamespace(model_dump_json=lambda:'{}'), self.usage)
            self.exercise.judge('my answer')
            self.assertEqual(judge.call_args.args[2][0]['主题'], '正态分布')
            self.assertEqual(judge.call_args.args[2][0]['知识点内容'], 'normal')

    def test_other_topic_rejected(self):
        unrelated = {**self.documents[0], '主题':'指数分布'}
        with patch('practice.get_knowledge.get_knowledge', return_value=[self.documents[0], unrelated]), \
             patch('practice.practice.feynman') as ask:
            with self.assertRaises(ValueError):
                self.exercise.ask('连续分布', '正态分布')
            ask.assert_not_called()

    def test_empty_selection_clears_previous_question(self):
        self.exercise._question = 'old question'
        self.exercise.question_record_id = 10
        with patch('practice.get_knowledge.get_knowledge', return_value=[]):
            with self.assertRaises(ValueError):
                self.exercise.ask('连续分布', '不存在')
        self.assertIsNone(self.exercise._question)
        self.assertIsNone(self.exercise.question_record_id)

    def test_blank_topic_rejected(self):
        with patch('practice.get_knowledge.get_knowledge') as query:
            with self.assertRaises(ValueError):
                self.exercise.ask('连续分布', '')
            query.assert_not_called()


if __name__ == '__main__':
    unittest.main()
