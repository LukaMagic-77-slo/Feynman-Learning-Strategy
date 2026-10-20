import { useEffect, useState } from 'react';
import { BookOpen, ChevronRight, Info } from 'lucide-react';

const GROUPS = ['函数', '数列极限', '函数极限', '连续性'];

export default function CalculusPage({ Markdown }) {
  const [catalog, setCatalog] = useState(null);
  const [selected, setSelected] = useState('functions-limits');
  const [open, setOpen] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/calculus/catalog', { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error('无法读取高等数学条目');
        return response.json();
      })
      .then(setCatalog)
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, []);

  const module = catalog?.modules.find(item => item.id === selected);
  const entries = catalog?.entries.filter(item => item.module_id === selected) || [];

  return <div className="page calculus-page">
    <div className="page-top"><div className="eyebrow"><span className="tiny-dot"/> 高等数学知识目录</div><span className="pill">独立模块 <ChevronRight size={12}/> 8 个子模块</span></div>
    <div className="calculus-intro"><h1>高等数学</h1><p>按学习顺序浏览知识。函数与极限已整理初稿，参考书核对完成后再用于知识问答。</p></div>
    {error && <div role="alert" className="error"><Info size={17}/>{error}</div>}
    {!catalog && !error && <p className="calculus-loading">正在读取知识目录…</p>}
    {catalog && <div className="calculus-layout">
      <nav className="calculus-modules" aria-label="高等数学子模块">
        {catalog.modules.map((item, index) => <button key={item.id} type="button" aria-current={selected === item.id ? 'page' : undefined} className={selected === item.id ? 'calculus-module active' : 'calculus-module'} onClick={() => {setSelected(item.id);setOpen(null);}}>
          <span className="calculus-module-number">{String(index + 1).padStart(2, '0')}</span><span className="calculus-module-copy"><strong>{item.title}</strong><small>{item.id === 'functions-limits' ? `${catalog.entries.length} 条初稿` : '待整理'}</small></span><ChevronRight size={15}/>
        </button>)}
      </nav>
      <section className="calculus-content" aria-live="polite">
        <div className="calculus-section-head"><div><span>第 {catalog.modules.findIndex(item => item.id === selected) + 1} 部分</span><h2>{module.title}</h2><p>{module.summary}</p></div><div className="calculus-section-count">{entries.length ? `${entries.length} 条知识` : '待整理'}</div></div>
        {entries.length ? <><div className="calculus-review"><Info size={16}/><span>{catalog.review_status}。这些条目供浏览和修改，目前尚未进入概率论问答或向量检索。</span></div>
          {GROUPS.map(group => {
            const items = entries.filter(item => item.group === group);
            if (!items.length) return null;
            return <section className="calculus-group" key={group}><h3>{group}<span>{items.length}</span></h3>
              <div className="calculus-entry-list">{items.map(item => <article className="calculus-entry" key={item.id}>
                <button type="button" className="calculus-entry-toggle" aria-expanded={open === item.id} onClick={() => setOpen(open === item.id ? null : item.id)}><BookOpen size={17}/><span>{item.topic}</span><ChevronRight size={16} className={open === item.id ? 'rotated' : ''}/></button>
                {open === item.id && <div className="calculus-entry-body"><Markdown>{item.content}</Markdown><div className="calculus-entry-meta"><span>{item.id}</span><span>{item.keywords.join(' · ')}</span></div></div>}
              </article>)}</div>
            </section>;
          })}</> : <div className="calculus-pending"><BookOpen size={26}/><h3>这一部分尚无条目</h3><p>目录已按课程顺序建立，后续逐部分整理并核对。</p></div>}
      </section>
    </div>}
  </div>;
}
