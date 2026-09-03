import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, KeyRound, ShieldCheck, X } from 'lucide-react';
import { api, post } from './api';
import type { Health } from './types';

type Connection = {id:string; name:string; provider:string; model:string};
const providers = [
  {id:'gemini', name:'Google Gemini', model:'gemini-flash-latest'},
  {id:'openai', name:'OpenAI', model:'', hint:'Exact model ID from your account'},
  {id:'groq', name:'Groq', model:'', hint:'Exact model ID from your account'},
  {id:'openrouter', name:'OpenRouter', model:'', hint:'provider/model-name'},
];

export default function ProviderSettings({health, onClose, onSaved}: {
  health?:Health; onClose:()=>void; onSaved:(health:Health)=>void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [connections,setConnections] = useState<Connection[]>([]);
  const [editing,setEditing] = useState<string>();
  const [name,setName] = useState('');
  const [current,setCurrent] = useState(health);
  const [provider, setProvider] = useState('gemini');
  const [model, setModel] = useState('gemini-flash-latest');
  const [key, setKey] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { void api<Connection[]>('/provider/connections').then(setConnections).catch(e=>setError(e.message)); const el=dialog.current; el?.showModal(); return () => el?.close(); }, []);
  async function save(reset=false) {
    setPending(true); setError('');
    try {
      const result=await api<Health>('/provider', reset ? {method:'DELETE'} : post({id:editing, name, provider, model:model.trim(), ...(key.trim() ? {api_key:key.trim()} : {})}));
      setKey(''); setCurrent(result); onSaved(result); setConnections(await api<Connection[]>('/provider/connections')); setEditing(undefined); setName('');
    } catch(e) { setError(e instanceof Error ? e.message : 'Could not update API settings.'); }
    finally { setPending(false); }
  }
  async function manage(id:string, remove=false) { setPending(true); setError(''); try { const result=await api<Health>(`/provider/connections/${id}${remove ? '' : '/activate'}`,remove ? {method:'DELETE'} : post()); setCurrent(result);onSaved(result);setConnections(await api<Connection[]>('/provider/connections')); if(editing===id){setEditing(undefined);setKey('');setName('');} } catch(e){setError(e instanceof Error ? e.message : 'Connection update failed.');} finally{setPending(false);} }
  return <dialog ref={dialog} className="provider-dialog" aria-labelledby="provider-title" onCancel={e => {e.preventDefault(); if(!pending) onClose();}}>
    <button className="settings-close" type="button" onClick={onClose} disabled={pending} aria-label="Close API settings"><X size={20}/></button>
    <div className="settings-icon"><KeyRound size={24}/></div>
    <span className="section-label">YOUR CONNECTION</span>
    <h2 id="provider-title">Bring your own intelligence.</h2>
    <p className="settings-intro">Choose an engine. Keep the same voice, sources, and workspace.</p>
    <div className="current-connection"><ShieldCheck size={17}/><span>{current?.cloud_available ? `${current.cloud_provider || "API"} · ${current.cloud_model}` : "No API configured"}<small>Server configuration</small></span></div>
    <div className="saved-connections">{connections.map(c=><div className="saved-connection" key={c.id}><span><strong>{c.name}</strong><small>{c.model}</small></span><button type="button" disabled={pending || current?.cloud_connection_id===c.id} onClick={()=>void manage(c.id)}>{current?.cloud_connection_id===c.id ? 'Active' : 'Use'}</button><button type="button" disabled={pending} onClick={()=>{setEditing(c.id);setName(c.name);setProvider(c.provider);setModel(c.model);setKey('');}}>Edit</button><button type="button" disabled={pending} aria-label={`Remove ${c.name}`} onClick={()=>void manage(c.id,true)}><X size={14}/></button></div>)}</div>
    <form onSubmit={e => {e.preventDefault(); void save();}}>
      <fieldset disabled={pending}>
        <label>Connection name<input value={name} maxLength={80} onChange={e=>setName(e.target.value)} placeholder="e.g. My fast model"/></label>
        <label>Provider<select value={provider} onChange={e => {const next=providers.find(p=>p.id===e.target.value)!;setProvider(next.id);setModel(next.model);setKey('');}}>{providers.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Model<input required value={model} maxLength={180} onChange={e=>setModel(e.target.value)} placeholder={providers.find(p=>p.id===provider)?.hint || 'gemini-flash-latest'}/></label>
        <label>API key<input required={!editing} type="password" autoComplete="off" spellCheck={false} minLength={8} maxLength={4096} value={key} onChange={e=>setKey(e.target.value)} placeholder={editing ? "Leave blank to keep the current key" : "Paste your provider key"}/></label>
        <details className="connection-details"><summary>Storage & privacy</summary><p className="key-note">Held in this local server’s memory. Never saved in your browser. Clears on server restart. Saving does not send a test request or switch modes.</p>
        <p className="key-note">In API mode, questions, conversation context and retrieved passages go to {providers.find(p=>p.id===provider)?.name}. Your provider’s usage charges apply.</p>
        </details>
        {health?.offline && <p role="status" className="settings-error">Offline mode is enabled. API generation stays disabled.</p>}
        {error && <p role="alert" className="settings-error">{error}</p>}
        <button className="primary connect-provider" type="submit">{pending ? 'Updating…' : editing ? 'Save changes' : 'Add connection'}<ArrowUpRight size={17}/></button>
        {current?.cloud_override && <button type="button" className="reset-provider" onClick={()=>void save(true)}>Use server default</button>}
      {editing && <button className="reset-provider" type="button" onClick={()=>{setEditing(undefined);setName('');setKey('');}}>Cancel editing</button>}</fieldset>
    </form>
  </dialog>;
}
