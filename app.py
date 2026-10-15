"""Streamlit入口：在项目根目录执行 uv run streamlit run app.py。"""
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

PROJECT_DIR = Path(__file__).resolve().parent
# 兼容现有课程代码的同目录导入，不修改后端导入路径。
sys.path[:0] = [str(PROJECT_DIR / 'monitoring'), str(PROJECT_DIR / 'evaluation'), str(PROJECT_DIR)]

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(PROJECT_DIR / '.env')

from assistant import create_assistant
from init_db import get_db_connection
from practice_record import PracticeWithRecord
from record_query import get_conversations, get_stats
from save_feedback import save_feedback
from practice.get_knowledge import get_sections, get_topics

LOGGER = logging.getLogger(__name__)
PURPOSES = {
    'qa_answer': '知识问答',
    'student_question': '学生出题',
    'explanation_judge': '解释评价',
}
SCORES = {'good': '解释充分', 'partial': '部分理解', 'bad': '需要重新梳理',
          'unjudgeable': '暂时无法评价'}


def report_error(message):
    LOGGER.exception(message)
    st.error(message + '。请检查终端日志；网络错误可稍后重试。')


def require_config():
    missing = [name for name in ['DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL',
                                'DASHSCOPE_MODEL', 'DATABASE_URL'] if not os.getenv(name)]
    if missing:
        raise ValueError('缺少项目.env配置：' + ', '.join(missing))


def record_snapshot(record):
    if record is None:
        return None
    return {'tokens': record.total_tokens, 'time': record.response_time,
            'cost': record.cost, 'model': record.model}


def show_usage(record):
    if record:
        st.caption(f"模型 {record['model']} · {record['tokens']:,} tokens · "
                   f"{record['time']:.2f} 秒 · 估算 ¥{record['cost']:.6f}")


def feedback_buttons(record_id, area):
    # 位于生成/评分form之外：反馈触发重跑，不重复生成。
    if record_id is None:
        st.caption('这次结果没有成功保存到数据库，暂不能提交反馈。')
        return
    st.caption('这条回答是否有帮助？' if area == 'qa' else '你认为这次评价合理吗？')
    vote_key = f'vote_{area}_{record_id}'
    up, down = st.columns(2)
    score = None
    if up.button('👍 有帮助' if area == 'qa' else '👍 合理', key=f'{vote_key}_up'):
        score = 1
    if down.button('👎 需改进' if area == 'qa' else '👎 不合理', key=f'{vote_key}_down'):
        score = -1
    if score is not None:
        try:
            save_feedback(record_id, 'user', score=score,
                          user_id=st.session_state['browser_id'])
            st.session_state[vote_key] = score
        except Exception:
            report_error('反馈保存失败，未确认提交')
    if vote_key in st.session_state:
        selected = '赞' if st.session_state[vote_key] == 1 else '踩'
        st.success(f'已记录你的反馈：{selected}。再次选择可修改。')


def qa_page():
    st.title('把疑问讲清楚')
    st.write('围绕连续分布提问，助手会从知识库寻找依据。')
    with st.form('qa_form'):
        question = st.text_area('你的问题', placeholder='例如：概率密度为什么可以大于 1？',
                                key='qa_question', height=110)
        submitted = st.form_submit_button('提问', type='primary')
    if submitted:
        if not question.strip():
            st.warning('请先输入问题。')
        else:
            try:
                require_config()
                with st.spinner('检索知识并生成回答，首次使用会加载嵌入模型…'):
                    if 'qa_assistant' not in st.session_state:
                        st.session_state['qa_assistant'] = create_assistant()
                    assistant = st.session_state['qa_assistant']
                    answer = assistant.rag(question.strip())
                    st.session_state['qa_result'] = {
                        'question': question.strip(), 'answer': answer,
                        'id': assistant.last_conversation_id,
                        'usage': record_snapshot(assistant.last_call),
                        'save_failed': assistant.last_monitor_error is not None,
                    }
            except Exception:
                report_error('本次问答未完成，下面如有内容则为上次成功结果')
    result = st.session_state.get('qa_result')
    if result:
        st.divider()
        st.subheader('回答')
        st.caption('对应问题：' + result['question'])
        st.markdown(result['answer'])
        show_usage(result['usage'])
        if result['save_failed']:
            st.warning('答案已生成，但调用记录保存失败。')
        feedback_buttons(result['id'], 'qa')


def practice_page():
    st.title('试着把知识教给我')
    st.write('你来当老师，AI 来当学生。用自己的话解释，再看看哪些地方可以讲得更清楚。')
    course = '概率论'
    try:
        sections = get_sections(course)
        if not sections:
            st.info('知识库还没有章节，请先执行向量知识入库。')
            return
        section = st.selectbox('先选择章节', sections, key='practice_section')
        topics = get_topics(course, section)
        if not topics:
            st.info('该章节下没有主题。')
            return
        # 章节作为key的一部分，避免跨章节保留不合法的主题选择。
        topic = st.selectbox('再选择主题', topics, key=f'practice_topic_{section}')
    except Exception:
        report_error('无法读取章节和主题，请确认数据库已启动')
        return

    selection = (course, section, topic)
    if st.session_state.get('practice_selection') != selection:
        for name in ['exercise', 'practice_question', 'practice_result', 'practice_explanation']:
            st.session_state.pop(name, None)
        st.session_state['practice_selection'] = selection

    if st.button('生成学生问题', key='generate_practice', type='primary'):
        # 新题是新一轮练习，清空旧评价，避免反馈关联错误。
        for name in ['exercise', 'practice_question', 'practice_result', 'practice_explanation']:
            st.session_state.pop(name, None)
        try:
            require_config()
            with st.spinner('学生正在根据所选主题组织问题…'):
                if 'practice_client' not in st.session_state:
                    st.session_state['practice_client'] = OpenAI(
                        api_key=os.environ['DASHSCOPE_API_KEY'],
                        base_url=os.environ['DASHSCOPE_BASE_URL'],
                        timeout=60.0, max_retries=0)
                exercise = PracticeWithRecord(st.session_state['practice_client'], course=course)
                question, _ = exercise.ask(section, topic)
                st.session_state['exercise'] = exercise
                st.session_state['practice_question'] = {
                    'text': question, 'usage': record_snapshot(exercise.last_call),
                    'save_failed': exercise.last_monitor_error is not None,
                }
        except Exception:
            report_error('本次出题未完成')

    question = st.session_state.get('practice_question')
    if not question:
        st.info('选择主题后，点击“生成学生问题”开始。')
        return
    st.divider()
    st.subheader('学生想问')
    st.markdown(question['text'])
    show_usage(question['usage'])
    if question['save_failed']:
        st.warning('问题已生成，但出题记录保存失败。')
    with st.form('explanation_form'):
        explanation = st.text_area('你的解释', key='practice_explanation', height=180,
                                   placeholder='试着讲清楚含义、原因，必要时举一个例子。')
        submitted = st.form_submit_button('提交解释并评价', type='primary')
    if submitted:
        if not explanation.strip():
            st.warning('请先写下你的解释。')
        else:
            try:
                with st.spinner('正在对照本次问题和知识资料评价…'):
                    exercise = st.session_state['exercise']
                    result, _ = exercise.judge(explanation.strip())
                    st.session_state['practice_result'] = {
                        'evaluation': result.model_dump(), 'explanation': explanation.strip(),
                        'id': exercise.judge_record_id,
                        'usage': record_snapshot(exercise.last_call),
                        'save_failed': exercise.last_monitor_error is not None,
                    }
            except Exception:
                report_error('本次评价未完成，下面如有内容则为上次成功评价')
    saved = st.session_state.get('practice_result')
    if saved:
        result = saved['evaluation']
        st.subheader('这次解释的反馈')
        with st.expander('本次被评价的解释'):
            st.write(saved['explanation'])
        st.markdown('**' + SCORES.get(result['score'], result['score']) + '**')
        st.write(result['reasoning'])
        left, right = st.columns(2)
        with left:
            st.markdown('**可补充的要点**')
            for point in result['missing_points']:
                st.write('• ' + point)
            if not result['missing_points']:
                st.caption('未指出必要遗漏。')
        with right:
            st.markdown('**需要修正的地方**')
            for error in result['errors']:
                st.write('• ' + error)
            if not result['errors']:
                st.caption('未指出明确错误。')
        st.info(result['suggestion'])
        st.caption('这是对本次解释的评价，不代表对整个主题掌握程度的最终结论。')
        show_usage(saved['usage'])
        if saved['save_failed']:
            st.warning('评价已生成，但记录保存失败。')
        feedback_buttons(saved['id'], 'practice')


def dashboard_page():
    st.title('学习与调用记录')
    st.caption('当前为本地单用户原型，展示此数据库的全部已保存成功调用，并非当前浏览器独有记录。')
    if st.button('刷新数据', key='refresh_dashboard'):
        pass  # 点击本身会触发重跑；统计不使用缓存。
    try:
        stats = get_stats()
        metrics = st.columns(4)
        metrics[0].metric('成功调用数', stats.total)
        metrics[1].metric('估算费用 · 人民币', f'¥{stats.total_cost:.6f}')
        metrics[2].metric('平均调用耗时', f'{stats.avg_response_time:.2f} 秒')
        metrics[3].metric('平均 Token', f'{stats.avg_tokens:,.0f}')
        st.caption('一次练习含出题和评价等多次调用。费用未计入未记录的失败/重试，也不等于实际扣款。')

        # Dashboard额外只读聚合；不改变原有后端查询接口。
        with get_db_connection() as conn:
            daily = conn.execute('''SELECT (timestamp AT TIME ZONE 'Asia/Shanghai')::date AS day,
                COUNT(*), SUM(total_tokens), SUM(cost) FROM conversations
                GROUP BY day ORDER BY day''').fetchall()
            votes = conn.execute('''SELECT c.purpose,
                COUNT(*) FILTER (WHERE f.score=1), COUNT(*) FILTER (WHERE f.score=-1)
                FROM feedback f JOIN conversations c ON c.id=f.conversation_id
                WHERE f.source='user' GROUP BY c.purpose ORDER BY c.purpose''').fetchall()
        if daily:
            st.subheader('每日用量')
            daily_df = pd.DataFrame(daily, columns=['日期', '调用次数', 'Token', '估算费用'])
            chart1, chart2 = st.columns(2)
            with chart1:
                st.caption('每日 Token')
                st.bar_chart(daily_df.set_index('日期')[['Token']])
            with chart2:
                st.caption('每日估算费用 · 元')
                st.line_chart(daily_df.set_index('日期')[['估算费用']])
        st.subheader('用户反馈')
        if votes:
            st.dataframe(pd.DataFrame([
                {'用途': PURPOSES.get(p, p), '赞': up, '踩': down}
                for p, up, down in votes]), hide_index=True, use_container_width=True)
        else:
            st.info('还没有用户反馈。')

        st.subheader('最近调用')
        limit = st.selectbox('显示条数', [20, 50, 100, 200], key='record_limit')
        records = get_conversations(limit=limit)
        if not records:
            st.info('暂无调用记录，完成一次问答或练习后可在此查看。')
            return
        df = pd.DataFrame([asdict(record) for record in records])
        df['用途'] = df['purpose'].map(lambda p: PURPOSES.get(p, p))
        st.dataframe(df[['id', 'timestamp', '用途', 'question', 'model', 'total_tokens',
                         'response_time', 'cost']], hide_index=True, use_container_width=True)
        st.download_button('下载当前列表 CSV', df.to_csv(index=False).encode('utf-8-sig'),
                           file_name='call_records.csv', mime='text/csv')
        record_id = st.selectbox('查看记录详情', df['id'].tolist(), key='record_detail')
        detail = next(record for record in records if record.id == record_id)
        with st.expander('输入、输出与关联信息', expanded=True):
            st.write('问题：', detail.question)
            if detail.session_id:
                st.caption('练习会话：' + detail.session_id)
            if detail.user_answer:
                st.markdown('**用户解释**')
                st.write(detail.user_answer)
            st.markdown('**模型输出**')
            if detail.purpose == 'explanation_judge':
                try:
                    st.json(json.loads(detail.answer))
                except (ValueError, TypeError):
                    st.write(detail.answer)
            else:
                st.markdown(detail.answer)
            st.markdown('**完整提示词**')
            st.code(detail.prompt, language=None)
            st.markdown('**System 指令**')
            st.code(detail.instructions, language=None)
    except Exception:
        report_error('无法读取监控数据，请确认数据库和监控表已初始化')


def main():
    st.set_page_config(page_title='费曼学习 · 概率论', page_icon='📘', layout='wide')
    st.markdown('''<style>
        .block-container {max-width: 1120px; padding-top: 2rem;}
        [data-testid="stMetric"] {background: #f1f5f9; padding: 16px; border-radius: 12px; color: #0f172a;}
        h1 {letter-spacing: -0.04em;}
    </style>''', unsafe_allow_html=True)
    st.session_state.setdefault('browser_id', str(uuid4()))
    with st.sidebar:
        st.title('费曼学习')
        st.caption('概率论 · 连续分布')
        page = st.radio('功能', ['知识问答', '费曼练习', 'Dashboard'], key='navigation')
        st.divider()
        st.caption('先理解，再用自己的话讲清楚。')
    if page == '知识问答':
        qa_page()
    elif page == '费曼练习':
        practice_page()
    else:
        dashboard_page()


if __name__ == '__main__':
    main()
