import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from data_ingest import load_knowledge_data
from vector import PgVectorStore, document_text, vec_to_str
from rag import RAG


class PipelineTests(unittest.TestCase):
    def test_data_and_text(self):
        docs = load_knowledge_data()
        self.assertEqual(len(docs), 40)
        self.assertIn(docs[0]['关键词'][0], document_text(docs[0]))

    def test_vector_rejects_nan(self):
        with self.assertRaises(ValueError):
            vec_to_str([float('nan')])

    def test_search_maps_fields_and_uses_bound_parameters(self):
        embedder = Mock()
        embedder.get_sentence_embedding_dimension.return_value = 2
        embedder.encode.return_value = [1, 0]
        store = PgVectorStore(embedder, 'unused', 'test-model')
        conn = Mock()
        conn.execute.side_effect = [
            SimpleNamespace(fetchone=lambda: ('test-model', 2)),
            SimpleNamespace(fetchall=lambda: [('k1','概率论','章节','主题','内容',['关键词'],0.9)]),
        ]
        context = Mock()
        context.__enter__ = Mock(return_value=conn)
        context.__exit__ = Mock(return_value=False)
        store._connect = Mock(return_value=context)
        rows = store.search('密度是什么？')
        self.assertEqual(rows[0]['知识点id'], 'k1')
        self.assertEqual(rows[0]['关键词'], ['关键词'])
        sql, params = conn.execute.call_args.args
        self.assertIn('<=>', sql)
        self.assertEqual(params[1], '概率论')

    def test_rag_calls_retriever_and_includes_source(self):
        index = Mock()
        index.search.return_value = [load_knowledge_data()[0]]
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(output_text='回答')
        rag = RAG(index, client, model='test-model')
        self.assertEqual(rag.rag('什么是密度？'), '回答')
        request = client.responses.create.call_args.kwargs
        self.assertIn('prob-cont-pdf-001', request['input'][1]['content'])
        self.assertEqual(request['model'], 'test-model')

    def test_empty_results_do_not_call_llm(self):
        index, client = Mock(), Mock()
        index.search.return_value = []
        RAG(index, client, model='test-model').rag('问题')
        client.responses.create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
