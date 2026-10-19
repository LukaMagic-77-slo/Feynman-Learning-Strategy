import { useEffect, useRef, useState } from 'react';
import { BookOpen, MessageCircle, GraduationCap, ChartNoAxesColumnIncreasing, ArrowUpRight, ArrowUp, ArrowRight, Plus, Leaf, Info, RefreshCw, ThumbsUp, ThumbsDown, Check, Loader2, X, Clock3, Coins, ChevronRight, Sparkles, LayoutGrid, CircleHelp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import HistorySidebar from './components/HistorySidebar';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { normalizeStudentMath } from './studentMath';
import { StairBooksArt, TeachBackArt } from './StudyIllustrations';
import appIcon from './assets/app-icon.svg';

async function api(path, options = {}) {
  const response = await fetch('/api' + path, {credentials:'same-origin', ...options,
    headers:{'Content-Type':'application/json', ...options.headers}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求内容不完整，请检查输入。');
  return data;
}
const post = (path, body) => api(path, {method:'POST', body:JSON.stringify(body)});
const money = n => '¥' + Number(n || 0).toFixed(5);
const purposes = {qa_answer:'知识问答',student_question:'学生出题',explanation_judge:'解释评价'};
const scoreLabels = {good:'理解得很清楚',partial:'已经抓住部分要点',bad:'再梳理一下核心概念',unjudgeable:'需要更多信息才能评价'};
function Markdown({children}) {
  const text = normalizeStudentMath(String(children || '').replace(/\\\[([\s\S]*?)\\\]/g, (_, x) => '\n$$\n' + x + '\n$$\n').replace(/\\\(([\s\S]*?)\\\)/g, (_, x) => '$' + x + '$'));
  return <div className="prose"><ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{text}</ReactMarkdown></div>;
}
function ErrorBox({message, close}) { return message && <div role="alert" className="error"><Info size={17}/><span>{message}</span>{close && <button aria-label="关闭提示" onClick={close}><X size={16}/></button>}</div>; }
function KnowledgeScope() {return <aside className="knowledge-scope" aria-label="知识库范围说明"><Info size={18}/><div><strong>当前为小规模知识库演示版</strong><p>仅支持数据库内已收录的知识点，目前聚焦概率论中的连续分布：概率密度函数、分布函数、均匀分布、正态分布和指数分布。不覆盖完整概率论课程；超出知识库范围的问题暂不支持，练习也仅限已收录主题。</p></div></aside>;}
function Usage({value}) {return value && <div className="usage"><span><Clock3 size={13}/>{value.seconds.toFixed(1)} 秒</span><span>{value.total_tokens.toLocaleString()} tokens</span><span>{money(value.estimated_cost)}</span><span className="muted">估算</span></div>;}
function Feedback({id, kind}) {
  const [vote, setVote] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function save(score) {setBusy(true);setError('');try {await post('/feedback',{record_id:id,score});setVote(score);} catch(e){setError(e.message);} finally{setBusy(false);}}
  if (!id) return <div className="small muted">本次结果未保存，暂不能提交反馈。</div>;
  return <div className="feedback"><span>{kind === 'judge' ? '这次评价合理吗？' : '这个解释有帮助吗？'}</span><button disabled={busy} aria-label="点赞" className={vote===1?'voted':''} onClick={()=>save(1)}><ThumbsUp size={15}/></button><button disabled={busy} aria-label="点踩" className={vote===-1?'voted':''} onClick={()=>save(-1)}><ThumbsDown size={15}/></button>{vote && <span className="vote-ok"><Check size={13}/>已记录，可修改</span>}{error && <span className="text-error" role="alert">{error}</span>}</div>;
}
function Busy({text}) {return <div className="busy"><Loader2 size={18} className="spin"/><div>{text}<span>请稍候，不需要重复提交</span></div></div>;}

function AskPage({state,setState,working,setWorking,onNewChat,onSaved,historyLoading}) {
  const [input,setInput] = useState(''), [error,setError] = useState('');
  const suggestions = ['概率密度为什么可以大于 1？','如何直观理解分布函数？','指数分布的无记忆性是什么意思？','正态分布如何进行标准化？'];
  const turns = state.turns || [];
  const bottom = useRef(null);
  useEffect(()=>{setInput('');setError('');},[state.chatId]);
  useEffect(()=>{bottom.current?.scrollIntoView({block:'end',behavior:'smooth'});},[turns.length]);
  async function submit(event) {
    event.preventDefault();
    if(!input.trim()||working||historyLoading)return;
    setWorking(true);setError('');
    const question=input.trim(),chatId=state.chatId||crypto.randomUUID();
    setState(old=>({...old,chatId}));
    try {
      const result=await post('/qa',{question,chat_id:chatId,request_id:crypto.randomUUID()});
      setState(old=>({...old,chatId,turns:[...(old.turns||[]),result]}));
      setInput('');
      if(result.history_id)localStorage.setItem('feynman_active_chat',chatId);
      onSaved();
    } catch(e){setError(e.message);} finally{setWorking(false);}
  }
  return <div className="page ask-page"><KnowledgeScope/><div className="page-top"><div className="eyebrow"><span className="tiny-dot"/> 知识问答</div><span className="pill">概率论 <ChevronRight size={12}/> 连续分布</span></div>
    {historyLoading?<Busy text="正在读取聊天历史…"/>:!turns.length ? <><div className="hero"><div className="hero-tag"><Sparkles size={14}/> 从一个好问题开始</div><h1>不止知道答案，<br/>更要<span>理解为什么。</span></h1><p>把模糊的概念变成清晰的理解。<br/>基于你的知识库，找到有依据、讲得明白的解释。</p><div className="formula-art" aria-hidden="true"><div className="art-orbit"/><div className="formula-card f1"><Markdown>{'$\\int f(x)\\,dx = 1$'}</Markdown><span>概率，藏在曲线下面。</span></div><div className="formula-card f2"><svg viewBox="0 0 180 80"><path className="curve-area" d="M5 65 C45 65 47 12 90 12 S135 65 175 65 Z"/><path className="curve-line" d="M5 65 C45 65 47 12 90 12 S135 65 175 65"/><path className="axis" d="M5 68H175"/></svg><span>从直觉到理解</span></div><div className="art-dot"/></div></div><div className="suggestions-label">还没想好？从这些问题开始 <ArrowUpRight size={14}/></div><div className="suggestions">{suggestions.map((q,i)=><button key={q} disabled={working} onClick={()=>setInput(q)}><span className="suggestion-number">0{i+1}</span><span>{q}</span><ArrowUpRight size={16}/></button>)}</div></> : <><div className="section-heading"><div><h1>把疑问讲清楚</h1><p>继续提问会结合本聊天中已保存的上下文；新建聊天将开启独立对话。</p></div><button className="secondary" disabled={working} onClick={onNewChat}><Plus size={15}/>新聊天</button></div><div className="chat-turns">{turns.map((turn,i)=><section className="chat-turn" key={turn.history_id||turn.id||i}><div className="user-bubble"><span className="avatar">你</span><div>{turn.question}</div></div><article className="answer-card"><div className="answer-label"><span className="brand-small">f.</span>费曼助手<span className="label-tag">知识库回答</span></div><Markdown>{turn.answer}</Markdown>{turn.sources?.length>0&&<div className="source-list"><span>参考知识</span>{turn.sources.map(source=><span className="source" title={source.id} key={source.id}><BookOpen size={12}/>{source.topic}</span>)}</div>}<Usage value={turn.usage}/>{turn.save_warning&&<ErrorBox message={turn.save_warning}/>}<Feedback id={turn.record_id}/>{turn.history_warning&&<ErrorBox message={turn.history_warning}/>}</article></section>)}</div></>}
    <ErrorBox message={error} close={()=>setError('')}/>{working&&<Busy text="正在检索知识并组织回答…"/>}
    <form className="composer" onSubmit={submit}><textarea aria-label="输入问题" value={input} onChange={e=>setInput(e.target.value)} placeholder={turns.length?"继续追问，或补充你的理解…":"写下你的疑问，让理解更进一步…"} disabled={working||historyLoading} maxLength={6000} rows={2} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();submit(e);}}}/><div className="composer-bottom"><span><BookOpen size={14}/> 基于概率论知识库 <span className="shortcut">Enter 发送 · Shift + Enter 换行</span></span><button aria-label="发送问题" disabled={!input.trim()||working||historyLoading}>{working?<Loader2 size={18} className="spin"/>:<ArrowUp size={20}/>}</button></div></form><p className="footnote">本机单用户历史 · 仅显示成功保存的问答 · AI 的解释可能存在偏差</p><div ref={bottom}/>
  </div>;
}
function PracticePage({state,setState,working,setWorking}) {
  const [sections,setSections]=useState([]),[topics,setTopics]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[explanation,setExplanation]=useState('');
  const generation=useRef(0);
  useEffect(()=>{const ctl=new AbortController();api('/sections',{signal:ctl.signal}).then(values=>{setSections(values);setState(old=>({...old,section:old.section||values[0]||''}));}).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>{if(!ctl.signal.aborted)setLoading(false);});return()=>ctl.abort();},[]);
  useEffect(()=>{if(!state.section)return;const ctl=new AbortController();setTopics([]);api('/topics?section='+encodeURIComponent(state.section),{signal:ctl.signal}).then(values=>{setTopics(values);setState(old=>({...old,topic:values.includes(old.topic)?old.topic:values[0]||''}));}).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>ctl.abort();},[state.section]);
  function select(values){generation.current++;setState(old=>({...old,...values,question:null,result:null}));setExplanation('');setError('');}
  async function ask(){if(working||!state.topic)return;setWorking(true);setError('');const rev=++generation.current;setState(old=>({...old,question:null,result:null}));setExplanation('');try{const q=await post('/practice/questions',{section:state.section,topic:state.topic,request_id:crypto.randomUUID()});if(rev===generation.current)setState(old=>({...old,question:q,result:null}));}catch(e){setError(e.message);}finally{setWorking(false);}}
  async function judge(event){event.preventDefault();if(working||!explanation.trim())return;setWorking(true);setError('');try{const result=await post('/practice/'+state.question.exercise_id+'/judge',{user_answer:explanation.trim(),request_id:crypto.randomUUID()});setState(old=>({...old,result}));}catch(e){setError(e.message);}finally{setWorking(false);}}
  return <div className="page practice-page"><KnowledgeScope/><div className="page-top"><div className="eyebrow"><span className="tiny-dot"/> 费曼练习</div><span className="pill"><GraduationCap size={14}/> 换个角色，检验理解</span></div><div className="section-heading section-heading--illustrated practice-heading"><div><h1>这一次，<span>你来当老师。</span></h1><p>用自己的话讲清楚，是理解最好的练习。</p></div><TeachBackArt/></div><div className="steps"><span className={!state.question?'active':''}><b>01</b>选择知识</span><i/><span className={state.question&&!state.result?'active':''}><b>02</b>讲给学生听</span><i/><span className={state.result?'active':''}><b>03</b>收获反馈</span></div>
    <section className="selection-card"><div className="card-heading"><BookOpen size={18}/><h2>今天想讲哪个知识点？</h2></div><div className="selection-grid"><label>章节<select aria-label="选择章节" value={state.section||''} disabled={loading||working} onChange={e=>select({section:e.target.value,topic:''})}>{sections.map(s=><option key={s}>{s}</option>)}</select></label><label>主题<select aria-label="选择主题" value={state.topic||''} disabled={!topics.length||working} onChange={e=>select({topic:e.target.value})}>{topics.map(t=><option key={t}>{t}</option>)}</select></label><button className="primary" onClick={ask} disabled={!state.topic||!topics.length||working}>{state.question?'换一道问题':'开始练习'}<ArrowRight size={16}/></button></div><span className="small muted">只使用所选主题的知识资料，不进行向量搜索。</span></section>
    <ErrorBox message={error} close={()=>setError('')}/>{!loading&&!sections.length&&!error&&<div className="empty"><BookOpen/><h3>知识库还没有内容</h3><p>请先在后端完成知识入库，再刷新页面。</p></div>}
    {working&&<Busy text={state.question?'正在认真听你的解释…':'学生正在组织一个好问题…'}/>}
    {!state.question?<div className="practice-empty"><div className="empty-orbits"><GraduationCap size={34}/></div><h3>教会别人，也是在教会自己。</h3><p>不必追求完美的措辞。先讲出你的理解，<br/>再一起找到遗漏与误区。</p><div className="tip"><Leaf size={16}/> 试着回答“为什么”，而不只是背出“是什么”。</div></div>:<><section className="student-card"><div className="student-avatar"><GraduationCap size={20}/></div><div><span className="eyebrow">你的 AI 学生</span><Markdown>{state.question.question}</Markdown><Usage value={state.question.usage}/></div></section>{state.question.save_warning&&<ErrorBox message={state.question.save_warning}/>}<form className="explanation-card" onSubmit={judge}><label htmlFor="explanation">现在，讲给我听 <span>用直觉、公式或一个小例子，都可以。</span></label><textarea id="explanation" placeholder="我的理解是…" value={explanation} onChange={e=>setExplanation(e.target.value)} rows={6} disabled={working} maxLength={12000}/><div className="explanation-bottom"><span>{explanation.length} / 12000</span><button className="primary" disabled={working||!explanation.trim()}>提交解释，看看反馈 <ArrowRight size={15}/></button></div></form></>}
    {state.result&&<section className="evaluation-card" data-score={state.result.evaluation.score}><div className="card-heading"><span className={'score-icon '+state.result.evaluation.score}>{state.result.evaluation.score==='good'?<Check size={20}/>:state.result.evaluation.score==='bad'?<X size={20}/>:<Info size={20}/>}</span><div><span className="eyebrow">本次学习反馈</span><h2>{scoreLabels[state.result.evaluation.score]}</h2></div></div><EvaluationBody evaluation={state.result.evaluation}/><details><summary>查看本次被评价的解释</summary><p>{state.result.user_answer}</p></details><Usage value={state.result.usage}/>{state.result.save_warning&&<ErrorBox message={state.result.save_warning}/>}<Feedback kind="judge" key={state.result.record_id||state.result.user_answer} id={state.result.record_id}/><p className="small muted">评价只针对这次解释，不代表你对整个主题的最终掌握程度。</p></section>}
  </div>;
}

function EvaluationBody({evaluation}) {
  return <><div className="evaluation-reason"><Markdown>{evaluation.reasoning}</Markdown></div><div className="evaluation-columns"><div><h3>可以补充的要点</h3>{evaluation.missing_points?.length?evaluation.missing_points.map((point,i)=><Markdown key={i}>{'· '+point}</Markdown>):<span className="small muted">没有发现必要的遗漏。</span>}</div><div><h3>需要修正的地方</h3>{evaluation.errors?.length?evaluation.errors.map((point,i)=><Markdown key={i}>{'· '+point}</Markdown>):<span className="small muted">没有发现明确的错误。</span>}</div></div><div className="next-step"><Leaf size={18}/><div><b>下一小步</b><Markdown>{evaluation.suggestion}</Markdown></div></div></>;
}

function Dashboard(){
  const [data,setData]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[revision,setRevision]=useState(0),[detail,setDetail]=useState(null),[filter,setFilter]=useState('all');
  useEffect(()=>{const ctl=new AbortController();setLoading(true);setError('');api('/dashboard?limit=100',{signal:ctl.signal}).then(setData).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>{if(!ctl.signal.aborted)setLoading(false);});return()=>ctl.abort();},[revision]);
  const rows=data?.records.filter(r=>filter==='all'||r.purpose===filter)||[];
  return <div className="page dashboard"><div className="page-top"><div className="eyebrow"><span className="tiny-dot"/> 学习记录</div><span className="pill">数据库全量统计</span></div><div className="section-heading section-heading--illustrated dashboard-heading"><div><h1>每一次学习，<span>都有迹可循。</span></h1><p>查看模型调用、用量与反馈，让学习过程更透明。</p></div><div className="heading-side"><StairBooksArt/><button className="secondary" disabled={loading} onClick={()=>setRevision(r=>r+1)}><RefreshCw size={15} className={loading?'spin':''}/>刷新</button></div></div><ErrorBox message={error}/>{loading&&!data&&<Busy text="正在读取调用记录…"/>}{data&&<><div className="stats-grid">{[[MessageCircle,'成功调用',data.stats.calls,'次模型调用'],[LayoutGrid,'Token 用量',data.stats.tokens.toLocaleString(),'累计输入与输出'],[Coins,'估算费用',money(data.stats.cost),'人民币 · 非实际账单'],[Clock3,'平均耗时',data.stats.seconds.toFixed(1)+' s','每次成功调用']].map(([Icon,label,value,note])=><div className="stat" key={label}><div><span>{label}</span><Icon size={17}/></div><strong>{value}</strong><small>{note}</small></div>)}</div><div className="dashboard-grid"><section className="chart-card"><div className="card-heading spread"><h2>每日 Token 用量</h2><span className="small muted">最近 14 个有记录的日期</span></div>{data.daily.length?<div className="bar-chart">{data.daily.map(day=><div className="bar-item" key={day.date}><div className="bar-track"><div className="bar" style={{height:Math.max(3,day.tokens/Math.max(...data.daily.map(x=>x.tokens),1)*100)+'%'}} title={`${day.date} · ${day.tokens} tokens · ${money(day.cost)}`}/></div><span>{day.date.slice(5)}</span></div>)}</div>:<div className="chart-empty">完成一次问答或练习后，用量将在这里出现。</div>}</section><section className="feedback-card"><span className="eyebrow">反馈概览</span><h2>用户反馈</h2><p>每一次反馈，帮助我们把解释讲得更好。</p><div className="vote-stats"><div><ThumbsUp size={19}/><strong>{data.feedback.up}</strong><span>赞</span></div><div><ThumbsDown size={19}/><strong>{data.feedback.down}</strong><span>踩</span></div></div></section></div><section className="records-card"><div className="card-heading spread"><h2>最近调用记录 <span className="count">{rows.length}</span></h2><select aria-label="筛选调用用途" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">全部用途</option>{Object.entries(purposes).map(([k,v])=><option value={k} key={k}>{v}</option>)}</select></div><div className="table-scroll"><table><thead><tr><th>问题 / 内容</th><th>用途</th><th>Token</th><th>耗时</th><th>估算费用</th><th/></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td><button className="record-title" onClick={()=>setDetail(row)}>{row.question}</button><small>#{row.id} · {new Date(row.timestamp).toLocaleString('zh-CN')}</small></td><td><span className="purpose-tag">{purposes[row.purpose]||row.purpose}</span></td><td>{row.tokens.toLocaleString()}</td><td>{row.seconds.toFixed(1)}s</td><td>{money(row.cost)}</td><td><button className="icon-button" aria-label={'查看记录'+row.id} onClick={()=>setDetail(row)}><ArrowUpRight size={16}/></button></td></tr>)}</tbody></table>{!rows.length&&<div className="empty"><BookOpen size={27}/><h3>暂时没有调用记录</h3><p>去问一个问题，或者开始一次费曼练习。</p></div>}</div></section><p className="footnote">本地单用户原型 · 展示数据库中全部已保存的成功调用 · 不包含未记录的失败与重试费用</p></>}{detail&&<div className="modal-backdrop" onClick={()=>setDetail(null)}><section role="dialog" aria-modal="true" aria-label="调用详情" className="detail-modal" onClick={e=>e.stopPropagation()}><div className="card-heading spread"><h2>调用详情 <span className="muted">#{detail.id}</span></h2><button className="icon-button" aria-label="关闭详情" onClick={()=>setDetail(null)}><X size={20}/></button></div><span className="purpose-tag">{purposes[detail.purpose]}</span><h3>{detail.question}</h3>{detail.user_answer&&<><h4>用户解释</h4><p>{detail.user_answer}</p></>}<h4>模型输出</h4>{detail.purpose==='explanation_judge'?<pre>{prettyJSON(detail.answer)}</pre>:<Markdown>{detail.answer}</Markdown>}<details><summary>完整提示词与指令</summary><h4>System</h4><pre>{detail.instructions}</pre><h4>Prompt</h4><pre>{detail.prompt}</pre></details><span className="small muted">{detail.model} · {detail.tokens} tokens · {money(detail.cost)}{detail.session_id&&' · 练习 '+detail.session_id}</span></section></div>}</div>;
}
function prettyJSON(text){try{return JSON.stringify(JSON.parse(text),null,2);}catch{return text;}}

export default function App(){
  const [page,setPage]=useState('qa'),[qa,setQa]=useState({chatId:null,turns:[]}),[practice,setPractice]=useState({section:'',topic:'',question:null,result:null}),[working,setWorking]=useState(false),[online,setOnline]=useState(null),[sessionError,setSessionError]=useState(''),[model,setModel]=useState(''),[sessionReady,setSessionReady]=useState(false);
  useEffect(()=>{let active=true;api('/session').then(data=>{if(active){setModel(data.model);setSessionReady(true);}}).catch(e=>{if(active)setSessionError(e.message);});api('/health').then(data=>{if(active)setOnline(data.database);}).catch(()=>{if(active)setOnline(false);});return()=>{active=false;};},[]);
  const [chats,setChats]=useState([]),[historyLoading,setHistoryLoading]=useState(false),[historyBusy,setHistoryBusy]=useState(false),[historyError,setHistoryError]=useState('');
  const historyRequest=useRef(0);
  async function refreshChats(){
    setHistoryLoading(true);setHistoryError('');
    try{setChats(await api('/chats'));}catch(e){setHistoryError('历史读取失败：'+e.message);}finally{setHistoryLoading(false);}
  }
  function newChat(){
    historyRequest.current++;setHistoryBusy(false);setPage('qa');
    setQa({chatId:crypto.randomUUID(),turns:[]});
    localStorage.removeItem('feynman_active_chat');
  }
  async function loadChat(chatId){
    const version=++historyRequest.current;
    setPage('qa');setHistoryBusy(true);setHistoryError('');
    try{
      const turns=await api('/chats/'+encodeURIComponent(chatId)+'/history');
      if(version!==historyRequest.current)return;
      setQa({chatId,turns});
      if(turns.length)localStorage.setItem('feynman_active_chat',chatId);
      else localStorage.removeItem('feynman_active_chat');
    }catch(e){if(version===historyRequest.current)setHistoryError('聊天加载失败：'+e.message);}
    finally{if(version===historyRequest.current)setHistoryBusy(false);}
  }
  useEffect(()=>{
    if(!sessionReady)return;
    refreshChats();
    const saved=localStorage.getItem('feynman_active_chat');
    if(saved)loadChat(saved);
  },[sessionReady]);
  const nav=[['qa',MessageCircle,'知识问答','Ask & understand'],['practice',GraduationCap,'费曼练习','Learn by teaching'],['dashboard',ChartNoAxesColumnIncreasing,'学习记录','Your learning, in view']];
  return <div className="app-shell" data-page={page}><aside className="sidebar"><a href="#" className="brand" onClick={e=>e.preventDefault()}><span className="brand-mark"><img src={appIcon} alt="f." width="64" height="64"/></span><div>费曼<span>LEARNING WORKSPACE</span></div></a><div className="workspace"><span className="workspace-icon"><BookOpen size={19}/></span><div><b>概率论学习空间</b><span>让理解真正发生</span></div><ChevronRight size={14}/></div><div className="nav-label">你的学习空间</div><nav>{nav.map(([id,Icon,label,sub])=><button key={id} data-section={id} aria-label={label} title={label} disabled={working||historyBusy} className={page===id?'nav-item selected':'nav-item'} onClick={()=>setPage(id)}><Icon size={20}/><span>{label}<small>{sub}</small></span>{page===id&&<span className="nav-dot"/>}</button>)}</nav><HistorySidebar chats={chats} activeId={qa.chatId} busy={working||historyBusy} loading={historyLoading} error={historyError} onNew={newChat} onSelect={loadChat} onRefresh={refreshChats}/><div className="sidebar-bottom"><span className={'status-dot '+(online===true?'ok':online===false?'bad':'')}/><span>{online===null?'正在连接知识库':online?'知识库已连接':'数据库暂不可用'}</span><span className="version">v0.1</span></div></aside><div className="main-shell"><header className="topbar"><div>学习工作台 <ChevronRight size={13}/><b>{nav.find(x=>x[0]===page)[2]}</b></div><span className="model-label"><span className="tiny-dot"/>{model||'本地学习空间'}</span></header><main>{sessionError?<div className="page"><ErrorBox message={'后端连接失败：'+sessionError}/><button className="secondary" onClick={()=>window.location.reload()}>重新连接</button></div>:!sessionReady?<div className="page"><Busy text="正在连接学习空间…"/></div>:page==='qa'?<AskPage state={qa} setState={setQa} working={working} setWorking={setWorking} onNewChat={newChat} onSaved={refreshChats} historyLoading={historyBusy}/>:page==='practice'?<PracticePage state={practice} setState={setPractice} working={working} setWorking={setWorking}/>:<Dashboard/>}</main><footer><span>FEYNMAN / 让知识成为理解</span><span>持续提问，慢慢想明白。 <Leaf size={12}/></span></footer></div></div>;
}
