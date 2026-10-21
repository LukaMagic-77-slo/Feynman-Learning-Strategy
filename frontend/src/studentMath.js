// 兼容旧的学生问题：只处理常见的分位数记法，不改动已有的 LaTeX 区段。
const mathSegment = /(\$\$[\s\S]*?\$\$|\$(?:\\.|[^$\\])+\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))/g;
const legacyNotation = /q_p\s*=\s*inf\s*\{\s*x\s*:\s*F\(x\)\s*≥\s*p\s*\}|F\(q_p\)\s*=\s*p\b|F\(x\)\s*=\s*(?:\d+(?:\.\d+)?|p)\b|p\s*=\s*\d+(?:\.\d+)?\b|q_p|F\(x\)|\bF\b|\bp\b|\binf\b/g;

function asLatex(match) {
  if (/^q_p\s*=\s*inf/.test(match)) return '$q_p=\\inf\\{x:F(x)\\ge p\\}$';
  if (match === 'inf') return '$\\inf$';
  return `$${match}$`;
}

export function normalizeStudentMath(question) {
  return String(question || '').split(mathSegment).map((part, index) =>
    index % 2 ? part : part.replace(legacyNotation, asLatex)
  ).join('');
}

// KaTeX does not implement \centernot; normalize common model output before parsing.
export function normalizeUnsupportedMath(text) {
  return String(text || '')
    .replace(/\\centernot\s*\\(?:implies|Rightarrow)\b/g, '\\nRightarrow')
    .replace(/\\centernot\s*\\(?:to|rightarrow)\b/g, '\\nrightarrow');
}
