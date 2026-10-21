import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { normalizeStudentMath, normalizeUnsupportedMath } from '../src/studentMath.js';

test('旧学生题的分位数记法能成为 KaTeX 下标和公式', () => {
  const question = '老师，在 F 连续时解 F(q_p)=p；定义 q_p=inf{x:F(x)≥p}，为什么用 inf 比 F(x)=0.5 更稳妥？';
  const formatted = normalizeStudentMath(question);
  const html = renderToStaticMarkup(React.createElement(ReactMarkdown,
    { remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] }, formatted));

  assert.match(formatted, /\$q_p=\\inf\\\{x:F\(x\)\\ge p\\\}\$/);
  assert.match(html, /class="katex"/);
  assert.match(html, /class="msupsub"/);
  assert.doesNotMatch(html, /<p>[^<]*q_p/);
});

test('已正确标记的 LaTeX 保持原样', () => {
  const question = '求 $q_p$，并解释 \\(F(x)\\) 与 $$q_p=\\inf\\{x:F(x)\\ge p\\}$$。';
  assert.equal(normalizeStudentMath(question), question);
});

test('模型输出的不推出符号可在旧回答中正常渲染', () => {
  const text = '有界 $a_n\\centernot \\implies a_n$ 收敛；$x\\centernot\\to a$。';
  const normalized = normalizeUnsupportedMath(text);
  const html = renderToStaticMarkup(React.createElement(ReactMarkdown,
    { remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] }, normalized));
  assert.match(normalized, /\\nRightarrow/);
  assert.match(normalized, /\\nrightarrow/);
  assert.doesNotMatch(html, /katex-error|centernot/);
  assert.match(html, /class="katex"/);
});
