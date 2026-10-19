import {useState} from 'react';
import {History, Plus, RefreshCw, X, MessageCircle} from 'lucide-react';

export default function HistorySidebar({chats,activeId,busy,loading,error,onNew,onSelect,onRefresh}) {
  const [open,setOpen]=useState(false);
  return <section className={'history-panel'+(open?' history-open':'')} aria-label="聊天历史">
    <button className="history-toggle" aria-label="打开聊天历史" title="聊天历史" disabled={busy} onClick={()=>setOpen(!open)}><History size={20}/></button>
    <div className="history-content">
      <div className="history-heading"><span>聊天历史</span><div><button aria-label="刷新聊天历史" title="刷新" disabled={busy||loading} onClick={onRefresh}><RefreshCw size={13}/></button><button className="history-close" aria-label="关闭聊天历史" onClick={()=>setOpen(false)}><X size={15}/></button></div></div>
      <button className="history-new" disabled={busy} onClick={()=>{onNew();setOpen(false);}}><Plus size={15}/>新建聊天</button>
      <div className="history-list">{loading&&<p className="history-hint">正在读取…</p>}{error&&<p className="history-error" role="alert">{error}</p>}{!loading&&!error&&!chats.length&&<p className="history-hint">完成一次问答后，聊天会出现在这里。</p>}{chats.map(chat=><button key={chat.chat_id} disabled={busy} aria-label={'打开聊天：'+chat.title} aria-current={activeId===chat.chat_id?'true':undefined} className={'history-item'+(activeId===chat.chat_id?' active':'')} title={chat.title} onClick={()=>{onSelect(chat.chat_id);setOpen(false);}}><MessageCircle size={13}/><span>{chat.title}</span><small>{chat.turns}</small></button>)}</div>
      <p className="history-hint history-scope">本地知识问答 · 最近 100 段聊天</p>
    </div>
  </section>;
}
