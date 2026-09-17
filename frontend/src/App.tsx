import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, AudioLines, BookOpen, Check, ChevronRight, CircleHelp, Database,
  ExternalLink, FileText, FlaskConical, GitBranch, Globe, Headphones, Library, LoaderCircle, MessageSquare,
  Mic, MicOff, Plus, RefreshCw, Send, Square, Trash2, Upload, X } from 'lucide-react';
import { api, post, hosted, workspaceReady, configureWorkspace, workspaceSocket, sessionKey } from './api';
import WorkspaceConnection from './WorkspaceConnection';
import { AudioEngine, emptyPlayback } from './audio';
import VoiceWorkspace from './VoiceWorkspace';
import { ProviderSwitch, ProviderContext } from './ProviderSwitch';
import ProviderSettings from './ProviderSettings';
import ReviewControls from './ReviewControls';
import { StudioHero, MotionButton } from './Studio';
import type { EvalRun, Health, Mode, NodeEvent, Passage, Provider, Source, Turn } from './types';

const starters = ['How does the Aurora field station get its power?', 'Compare the two sensor calibration schedules.',
  'What should the team do during a communications outage?'];
const fmt = (n: number | null | undefined, percent = false) => n == null ? '—' : percent ? `${Math.round(n * 100)}%` : `${(n / 1000).toFixed(1)}s`;

export default function App() {
  const [workspaceSettings, setWorkspaceSettings] = useState(false);
  const [workspaceRevision, setWorkspaceRevision] = useState(0);
  const [providerSettings, setProviderSettings] = useState(false);
  const [page, setPage] = useState('workspace');
  const [sources, setSources] = useState<Source[]>([]);
  const [health, setHealth] = useState<Health>();
  const [modelReady, setModelReady] = useState<boolean | null>(null);
  const [mode, setMode] = useState<Mode>('graph');
  const [provider, setProvider] = useState<Provider>('local');
  const [session, setSession] = useState('');
  const [connected, setConnected] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [nodes, setNodes] = useState<NodeEvent[]>([]);
  const [passages, setPassages] = useState<Passage[]>([]);
  const [busy, setBusy] = useState(false);
  const [matches,setMatches] = useState<{id:string;title:string;match:string}[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [voice, setVoice] = useState<'off' | 'loading' | 'on'>('off');
  const [energy, setEnergy] = useState(0);
  const [playback, setPlayback] = useState(emptyPlayback);
  const [selected, setSelected] = useState<Passage>();
  const [sourceDetail, setSourceDetail] = useState<Source>();
  const [url, setUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [activeRun, setActiveRun] = useState('');
  const ws = useRef<WebSocket | undefined>(undefined);
  const audio = useRef(new AudioEngine());
  const activeTurn = useRef<string | null>(null);
  const voiceReady = useRef(false);
  const options = useRef({mode, provider});
  const end = useRef<HTMLDivElement>(null);
  const studio = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const replaceInput = useRef<HTMLInputElement>(null);
  const replaceId = useRef('');
  const mounted = useRef(true);
  const connectionAttempt = useRef(0);
  options.current = {mode, provider};

  function send(event: Record<string, unknown>) { if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(event)); }
  function chooseProvider(next: Provider) {
    if (busy || voice !== 'off' || audio.current.playing.size) return;
    setProvider(next); setError(''); setNotice('');
  }
  function interrupt() {
    audio.current.stopPlayback();
    const old = activeTurn.current; activeTurn.current = null;
    setTurns(ts => ts.map(t => t.id === old && t.status === 'running' ? {...t, status: 'interrupted'} : t));
    setBusy(false); send({type: 'cancel'});
  }
  async function refresh() {
    const [items, status, evaluations] = await Promise.all([api<Source[]>('/sources'), api<Health>('/health'), api<EvalRun[]>('/evaluations')]);
    if (!mounted.current) return;
    setSources(items); setHealth(status); setRuns(evaluations);
  }
  async function connect(newSession = false) {
    const attempt = ++connectionAttempt.current;
    setConnected(false);
    ws.current?.close(); audio.current.stopPlayback(); audio.current.stopCapture();
    voiceReady.current = false; setVoice('off'); activeTurn.current = null; setBusy(false);
    let id = newSession ? null : localStorage.getItem(sessionKey());
    let history: Turn[] = [];
    if (id) { try { history = await api<Turn[]>(`/sessions/${id}`); } catch { id = null; } }
    if (!mounted.current || attempt !== connectionAttempt.current || !workspaceReady()) return;
    if (!id) id = (await api<{id: string}>('/sessions', post())).id;
    if (!mounted.current || attempt !== connectionAttempt.current) return;
    localStorage.setItem(sessionKey(), id); setSession(id); setPlayback(emptyPlayback()); setTurns(history); setNodes([]); setPassages([]);
    const socket = workspaceSocket(id);
    ws.current = socket;
    socket.onerror = () => { if (ws.current === socket) setError('Streaming connection failed. Check local network permission, the pairing token, and that the backend is running. You can also open the local app.'); };
    socket.onclose = () => { if (ws.current === socket) { setConnected(false); setBusy(false); audio.current.stopPlayback(); audio.current.stopCapture(); voiceReady.current = false; setVoice('off'); } };
    socket.onmessage = event => {
      if (ws.current !== socket) return;
      const e = JSON.parse(event.data);
      if (e.type === 'ready') { setConnected(true); send({type: 'configure', ...options.current}); return; }
      if (e.type === 'turn_start') {
        audio.current.stopPlayback(); activeTurn.current = e.turn_id; setPlayback(emptyPlayback()); setBusy(true); setNodes([]); setPassages([]);
        setTurns(ts => [...ts, {id: e.turn_id, question: '', answer: '', status: 'running', mode: e.mode, provider: e.provider, citations: []}]); return;
      }
      if (e.type === 'speech_start' || e.type === 'cancelled') {
        audio.current.stopPlayback();
        const old = e.cancelled_turn_id || activeTurn.current;
        if (old === activeTurn.current) activeTurn.current = null;
        setTurns(ts => ts.map(t => t.id === old && (t.status === 'running' || e.interrupted_playback) ? {...t, status: 'interrupted'} : t));
        setBusy(false); return;
      }
      if (e.type === 'voice_ready') { voiceReady.current = true; setVoice('on'); return; }
      if (e.type === 'voice_stopped') { voiceReady.current = false; setVoice('off'); return; }
      if (e.turn_id && e.turn_id !== activeTurn.current) return;
      if (e.type === 'transcript') setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, question: e.text} : t));
      if (e.type === 'answer_delta') setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, answer: t.answer + e.text} : t));
      if (e.type === 'node') setNodes(ns => e.status === 'running' ? [...ns, e] : ns.map((n, i) => i === ns.length - 1 ? e : n));
      if (e.type === 'passages') setPassages(e.passages);
      if (e.type === 'citations') setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, citations: e.citations} : t));
      if (e.type === 'audio') audio.current.enqueue(e.wav, () => {
        if (activeTurn.current === e.turn_id) {
          send({type: 'played', turn_id: e.turn_id, chunk_id: e.chunk_id});
          setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, played: (t.played || '') + e.text + ' '} : t));
        }
      }, {turnId:e.turn_id, text:e.text});
      if (e.type === 'turn_end') { setBusy(false); setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, status: e.status, trace: e.trace} : t)); }
      if (e.type === 'warning') setNotice(e.message);
      if (e.type === 'error') {
        audio.current.stopPlayback();
        setError(e.message); setBusy(false);
        setTurns(ts => ts.map(t => t.id === e.turn_id ? {...t, status: 'error'} : t));
        if (!voiceReady.current) { audio.current.stopCapture(); setVoice('off'); }
      }
    };
  }

  useEffect(() => {
    mounted.current = true;
    if (!workspaceReady()) return;
    audio.current.onPlayback = snapshot => {if (mounted.current && snapshot.turnId === activeTurn.current) setPlayback(snapshot);};
    let disposed = false;
    void refresh().then(() => {if (!disposed) return connect();}).catch(e => {if (!disposed) setError(e.message);});
    void api<{ready: boolean}>('/models/status').then(s => setModelReady(s.ready)).catch(() => {});
    const timer = setInterval(() => { void refresh().catch(() => {}); }, 3000);
    const modelTimer = setInterval(() => { void api<{ready: boolean}>('/models/status').then(s => setModelReady(s.ready)).catch(() => {}); }, 15000);
    return () => { disposed = true; ++connectionAttempt.current; mounted.current = false; audio.current.onPlayback = undefined; clearInterval(timer); clearInterval(modelTimer); ws.current?.close(); audio.current.close(); };
  }, [workspaceRevision]);
  useEffect(() => { send({type: 'configure', mode, provider}); }, [mode, provider]);
  useEffect(() => { if (busy) end.current?.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest'}); }, [turns.length, busy]);

  const matchQuery = draft.trim() || turns.at(-1)?.question || '';
  useEffect(() => {
    const controller = new AbortController();
    if(!workspaceReady() || matchQuery.length < 3) {setMatches([]);return;}
    setMatches([]);
    const timer=setTimeout(()=>{ void api<{id:string;title:string;match:string}[]>(`/suggestions?q=${encodeURIComponent(matchQuery)}`,{signal:controller.signal}).then(setMatches).catch(()=>{}); },300);
    return ()=>{clearTimeout(timer);controller.abort();};
  },[matchQuery]);

  async function ask(text = draft) {
    if (!text.trim() || !connected) return;
    if (provider === 'cloud' && !health?.cloud_available) {setProviderSettings(true);return;}
    setError(''); setNotice(''); setDraft('');
    audio.current.stopPlayback(); await audio.current.prepare();
    send({type: 'text', text: text.trim(), mode, provider});
  }
  async function toggleVoice() {
    if (voice !== 'off') { voiceReady.current = false; audio.current.stopCapture(); interrupt(); send({type: 'voice_stop'}); setVoice('off'); return; }
    if (provider === 'cloud' && !health?.cloud_available) {setProviderSettings(true);return;}
    setError(''); setVoice('loading');
    try {
      await audio.current.capture((pcm, level, detected) => {
        setEnergy(level);
        if (detected && audio.current.playing.size) interrupt();
        if (voiceReady.current && ws.current?.readyState === WebSocket.OPEN && ws.current.bufferedAmount < 65536) ws.current.send(pcm);
      });
      send({type: 'voice_start', mode, provider});
    } catch (e) { audio.current.stopCapture(); setVoice('off'); setError(String(e)); }
  }
  async function upload(file: File, replace = false) {
    setImporting(true); setError('');
    try {
      const form = new FormData(); form.append('file', file);
      const result = await api<{duplicate?: boolean}>(replace ? `/sources/${replaceId.current}/replace` : '/sources/upload', {method: 'POST', body: form});
      setNotice(result.duplicate ? 'This document is already in your library.' : 'Import queued. First-time embedding downloads may take a few minutes.'); await refresh();
    } catch (e) { setError(String(e)); } finally { setImporting(false); }
  }
  async function action(fn: () => Promise<unknown>) { try { setError(''); await fn(); await refresh(); } catch (e) { setError(String(e)); } }
  async function openSource(id: string) { try { setSourceDetail(await api<Source>(`/sources/${id}`)); } catch(e) { setError(String(e)); } }
  function changeWorkspace(address: string, token: string) {
    ++connectionAttempt.current;
    ws.current?.close(); ws.current = undefined;
    audio.current.stopPlayback(); audio.current.stopCapture();
    activeTurn.current = null; voiceReady.current = false;
    configureWorkspace(address, token);
    setConnected(false); setBusy(false); setVoice('off'); setPlayback(emptyPlayback());
    setSources([]);setTurns([]);setPassages([]);setNodes([]);setRuns([]);setHealth(undefined);
    setModelReady(null);setSession('');setDraft('');setMatches([]);setSelected(undefined);setSourceDetail(undefined);
    setProviderSettings(false);setProvider('local');setError('');setNotice('');setWorkspaceSettings(false);
    setWorkspaceRevision(v=>v+1);
  }
  const readyCount = sources.filter(s => s.version > 0).length;
  const PageHeading = page === 'workspace' ? 'h2' : 'h1';
  const run = runs.find(r => r.id === activeRun) || runs[0];

  return <div className="app-shell" data-provider={provider}>
    <div className="ambient-landscape" aria-hidden="true"/><a className="skip-link" href="#studio">Skip to workspace</a>
    <header className="site-header">
      <a className="brand" href="#" onClick={e => {e.preventDefault(); setPage('workspace');}} aria-label="LocalVoice home"><span className="brand-mark"><AudioLines size={25}/></span><span>Localvoice<span className="brand-ai">STUDIO</span></span></a>
      <nav aria-label="Main navigation">{[['workspace','Studio'],['library','Library'],['evaluation','Evaluations'],['about','About']].map(([key,label],i) => <button key={key} aria-current={page === key ? 'page' : undefined} className={page === key ? 'nav-item active' : 'nav-item'} onClick={() => {setPage(key); window.scrollTo({top:0, behavior:'instant'});}}><span className="nav-number">0{i+1}</span>{label}</button>)}</nav>
      <ProviderSwitch provider={provider} available={!!health?.cloud_available} locked={busy || voice !== 'off' || playback.speaking} onChange={chooseProvider}/>
    </header>
    {page === 'workspace' && <StudioHero provider={provider} voice={voice} connected={connected} energy={energy} onVoice={() => void toggleVoice()} onEnter={() => {studio.current?.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}); studio.current?.focus({preventScroll:true});}}/>}

    <main id="studio" ref={studio} tabIndex={-1}>
      <ProviderContext provider={provider} health={health} ready={modelReady}/><div className="connection-settings-row"><button className="secondary" disabled={busy || voice !== 'off' || playback.speaking} onClick={() => provider === 'local' ? setWorkspaceSettings(true) : workspaceReady() ? setProviderSettings(true) : setWorkspaceSettings(true)}>{provider === 'local' ? connected ? 'Local workspace connected' : 'Connect local workspace' : 'API settings'} {provider === 'local' && connected ? <span className="workspace-connected-mark" aria-label="Connected"><Check size={14} aria-hidden="true"/></span> : <ExternalLink size={14}/>}</button>{hosted && workspaceReady() && <button className="secondary" onClick={()=>changeWorkspace('', '')}>Disconnect workspace</button>}</div>
      <header className="topbar"><div className="breadcrumb">THE WORKSPACE <ChevronRight size={14}/><strong>{page === 'workspace' ? 'Conversation' : page === 'library' ? 'Knowledge library' : page === 'evaluation' ? 'Evaluation lab' : 'Setup & architecture'}</strong></div><div className="connection"><span className={`dot ${connected ? 'green' : ''}`}/>{connected ? 'Backend connected' : 'Disconnected'}{!connected && <button onClick={() => hosted ? setWorkspaceSettings(true) : void connect().catch(e => setError(e.message))}>Reconnect</button>}</div></header>
      {error && <div className="banner error" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={17}/></button></div>}
      {notice && <div className="banner" role="status"><span>{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={17}/></button></div>}
      <div className="page-heading"><div><div className="eyebrow">{page === 'workspace' ? '01 / CONVERSATION' : page === 'library' ? '02 / SOURCES' : page === 'evaluation' ? '03 / EVALUATIONS' : '04 / SETUP'}</div><PageHeading>{page === 'workspace' ? 'Your conversation.' : page === 'library' ? 'Knowledge library.' : page === 'evaluation' ? 'Evaluate your answers.' : 'Setup & architecture.'}</PageHeading><p>{page === 'workspace' ? 'Chat naturally, explore ideas, or ask about your documents.' : page === 'library' ? 'Turn documents and public web pages into a searchable knowledge base.' : page === 'evaluation' ? 'Compare retrieval paths on the same questions, sources, and model.' : 'Local storage, transparent workflows, and a voice you can interrupt.'}</p></div>{page === 'workspace' && <MotionButton className="secondary" onClick={() => void connect(true).catch(e => setError(e.message))}><Plus size={16}/> New conversation</MotionButton>}</div>

      {page === 'workspace' && <>
        <VoiceWorkspace voice={voice} connected={connected} busy={busy} energy={energy} question={turns.at(-1)?.question}
          playback={playback} onVoice={() => void toggleVoice()} onStop={interrupt}
          onType={() => {document.querySelector<HTMLInputElement>('.composer input')?.focus();}}/>
        <div className="workspace-controls"><div className="segmented" aria-label="Retrieval mode"><button disabled={busy || voice !== 'off'} aria-pressed={mode === 'baseline'} className={mode === 'baseline' ? 'selected' : ''} onClick={() => setMode('baseline')}><Database size={15}/>Baseline RAG</button><button disabled={busy || voice !== 'off'} aria-pressed={mode === 'graph'} className={mode === 'graph' ? 'selected' : ''} onClick={() => setMode('graph')}><GitBranch size={15}/>Graph RAG<span>1 RETRY</span></button></div><span className="active-engine"><span className="dot green"/>{provider === 'cloud' ? (health?.cloud_backend === 'gemini' ? 'Gemini API' : 'Cloud API') : 'Local generation'}</span></div>
        {provider === 'cloud' && <div className="privacy-note"><Globe size={14}/>Cloud mode sends your question, conversation context, and retrieved passages to the configured provider.</div>}
        {provider === 'local' && modelReady === false && <div className="privacy-note"><CircleHelp size={14}/>{health?.local_backend === 'lmstudio' ? `Local generation is not ready. Start the LM Studio server and load ${health?.local_model}.` : `Local generation is not ready. Start Ollama and run: ollama pull ${health?.local_model || 'qwen3:4b'}`}</div>}
        <div className="workspace-grid"><section className="conversation panel">
          <div className="panel-title"><span><MessageSquare size={16}/> Conversation</span><span className="muted mono">{session ? session.slice(0, 8) : 'CONNECTING'}</span></div>
          <div className="messages" aria-live="polite">
            {!turns.length && <div className="welcome"><div className="welcome-symbol" aria-hidden="true">✳</div><div className="eyebrow">ASK YOUR SOURCES</div><h2>Start with a question.</h2><p>Ask a question or start a voice conversation.<br/>Bring an idea, a question, or a document.</p><div className="suggestions">{starters.map((q, i) => <button key={q} onClick={() => void ask(q)} disabled={!connected}><span className="suggestion-number">0{i + 1}</span><span>{q}</span><ArrowRight size={16}/></button>)}</div>{!readyCount && <button className="text-button" onClick={() => void action(() => api('/demo/import', post()))}><BookOpen size={15}/> Start with the Aurora demo corpus</button>}</div>}
            {turns.map(t => <div className="turn" key={t.id}><div className="question"><span className="avatar">Y</span><div><small>YOU</small><p>{t.question || 'Transcribing…'}</p></div></div><div className="answer"><span className="avatar ai"><AudioLines size={16}/></span><div><small>LOCALVOICE <span>{t.mode === 'graph' ? 'GRAPH RAG' : 'BASELINE'} · {t.provider === 'cloud' ? 'API' : 'LOCAL'}</span></small><p>{t.answer || (t.status === 'running' ? 'Finding the relevant evidence…' : 'No answer generated.')}{t.status === 'running' && <span className="cursor"/>}</p>{t.citations.length > 0 && <div className="citation-list">{t.citations.map(c => <button key={c.id} onClick={() => setSelected(c)}><span>{c.number}</span>{c.title}{c.page && ` · p.${c.page}`}</button>)}</div>}<div className="turn-meta">{t.status === 'running' ? <><LoaderCircle size={12} className="spin"/> Working</> : <>{t.status === 'complete' ? <Check size={12}/> : <Square size={11}/>} {t.status}</>}{t.trace?.elapsed_ms && <> · {fmt(t.trace.elapsed_ms)}</>}{t.trace?.first_audio_ms && <> · first audio {fmt(t.trace.first_audio_ms)}</>}</div>{t.played && <details className="played"><summary>Audio confirmed played</summary>{t.played}</details>}</div></div></div>)}
            <div ref={end}/>
          </div>
          <div className="composer-area">
            {matches.length>0 && <div className="closest-matches" aria-label="Suggested sources"><span>Did you mean?</span>{matches.map(m=><button key={m.id} type="button" disabled={busy} title={m.match} onClick={()=>setDraft(`${matchQuery}\nUse "${m.title}" as the source.`)}>{m.title}<ArrowRight size={12}/></button>)}</div>}{voice !== 'off' && <div className="voice-status"><span className="voice-pulse" style={{transform: `scale(${1 + Math.min(energy * 10, .8)})`}}/>{voice === 'loading' ? 'Loading local speech models…' : 'Listening · speak naturally to interrupt'}<span>ENGLISH</span></div>}
            <form className="composer" onSubmit={e => {e.preventDefault(); void ask();}}><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Ask your knowledge base…" aria-label="Your question" maxLength={8000}/><button type="button" className={`mic-button ${voice !== 'off' ? 'listening' : ''}`} disabled={!connected || voice === 'loading'} onClick={() => void toggleVoice()} aria-label={voice === 'off' ? 'Start voice conversation' : 'Stop voice conversation'}>{voice === 'loading' ? <LoaderCircle className="spin" size={19}/> : voice === 'on' ? <MicOff size={19}/> : <Mic size={19}/>}</button>{busy ? <button type="button" className="send-button" onClick={interrupt} aria-label="Stop answer"><Square size={16}/></button> : <button className="send-button" disabled={!draft.trim() || !connected} aria-label="Send question"><Send size={17}/></button>}</form>
            <div className="composer-foot"><span><Headphones size={12}/> Headphones recommended for voice</span><span>{readyCount} available source{readyCount !== 1 ? 's' : ''}</span></div>
          </div>
        </section><aside className="inspector"><section className="panel workflow"><div className="panel-title"><span><GitBranch size={16}/> Workflow</span><span className="tiny-pill">LIVE</span></div><div className="workflow-intro">{mode === 'graph' ? 'A bounded path from question to evidence.' : 'A direct path from retrieval to answer.'}</div><div className="node-list">{(nodes.length ? nodes : (mode === 'graph' ? ['resolve','retrieve','assess','answer'] : ['retrieve','answer']).map(node => ({node, status: 'waiting'} as NodeEvent))).map((n, i) => <div className={`graph-node ${n.status}`} key={`${n.node}-${i}`}><span className="node-symbol">{n.status === 'complete' ? <Check size={13}/> : n.status === 'running' ? <LoaderCircle size={13} className="spin"/> : <span>{i + 1}</span>}</span><div><strong>{({route:'Understand intent',chat:'Conversation',resolve:'Resolve question',retrieve:'Retrieve evidence',assess:'Assess support',rewrite:'Refine query',answer:'Generate answer',abstain:'Explain evidence gap'} as Record<string,string>)[n.node]}</strong>{n.reason && <p>{n.reason}</p>}</div><small>{n.elapsed_ms != null ? fmt(n.elapsed_ms) : n.status === 'waiting' ? '—' : '…'}</small></div>)}</div><div className="workflow-footer"><span className="dot green"/> {mode === 'graph' ? 'At most 2 retrieval attempts' : 'One retrieval, one answer'}</div></section>
          <section className="panel evidence-panel"><div className="panel-title"><span><FileText size={16}/> Retrieved evidence</span><span className="count">{passages.length}</span></div>{passages.length ? passages.map((p, i) => <button className="passage-preview" key={p.id} onClick={() => setSelected(p)}><div><span className="evidence-index">{i + 1}</span><strong>{p.title}</strong><ExternalLink size={12}/></div><p>{p.text.slice(0, 155)}…</p><small>{p.page ? `Page ${p.page}` : p.section || 'Text passage'} · score {p.score?.toFixed(3)}</small></button>) : <div className="empty-evidence"><BookOpen size={28}/><p>Evidence appears here<br/>when you ask a question.</p><small>Open a passage to inspect its source.</small></div>}</section>
        </aside></div>
      </>}

      {page === 'library' && <><div className="library-actions"><button className="primary" disabled={importing} onClick={() => fileInput.current?.click()}><Upload size={16}/> Upload documents</button><button className="secondary" onClick={() => void action(() => api('/demo/import', post()))}><BookOpen size={16}/> Import demo corpus</button><details className="hover-details"><summary aria-label="Supported uploads"><CircleHelp size={16}/></summary><p>PDF, Markdown, TXT. Up to 20 MB. Scanned PDFs need OCR first.</p></details></div><form className="url-form panel" onSubmit={e => {e.preventDefault(); void action(async () => {await api('/sources/url', post({url})); setUrl('');});}}><Globe size={18}/><input type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com/a-page-to-remember" aria-label="Public page URL"/><button className="secondary">Import page <ArrowRight size={14}/></button></form><div className="source-grid">{sources.map(s => <article className="panel source-card" key={s.id}><div className="source-top"><span className="file-icon">{s.kind === 'url' ? <Globe size={22}/> : <FileText size={22}/>}</span><span className={`status-badge ${s.status}`}>{s.status}</span></div><h3><button onClick={() => void openSource(s.id)}>{s.title}</button></h3><p>{s.kind.toUpperCase()} · {s.chunks} passages · version {s.version}</p>{['queued','indexing'].includes(s.status) && <progress max={100} value={s.progress}/>} {s.error && <div className="source-error">{s.error}{s.version > 0 && ' Previous indexed version remains available.'}</div>}<div className="source-actions"><button onClick={() => void openSource(s.id)}>View passages <ArrowRight size={13}/></button><button aria-label={`Refresh ${s.title}`} disabled={['queued','indexing'].includes(s.status)} onClick={() => void action(() => api(`/sources/${s.id}/refresh`, post()))}><RefreshCw size={15}/></button>{s.kind !== 'url' && <button aria-label={`Replace ${s.title}`} disabled={['queued','indexing'].includes(s.status)} onClick={() => {replaceId.current = s.id; replaceInput.current?.click();}}><Upload size={15}/></button>}<button aria-label={`Delete ${s.title}`} onClick={() => void action(() => api(`/sources/${s.id}`, {method: 'DELETE'}))}><Trash2 size={15}/></button></div></article>)}</div>{!sources.length && <div className="large-empty"><Library size={40}/><h2>A home for your knowledge.</h2><p>Add your first source above, or import the fictional Aurora field-station documents.</p></div>}</>}

      {page === 'evaluation' && <><div className="eval-toolbar"><button className="primary" disabled={runs.some(r => r.status === 'running')} onClick={() => void action(async () => {const r = await api<{id:string}>('/evaluations', post({provider})); setActiveRun(r.id);})}><FlaskConical size={16}/> Run 40-question benchmark</button><select aria-label="Evaluation provider" value={provider} disabled={busy || voice !== 'off' || playback.speaking} onChange={e => chooseProvider(e.target.value as Provider)}><option value="local">Local model</option><option value="cloud" disabled={!health?.cloud_available}>{health?.cloud_provider || 'API'}</option></select><select aria-label="Evaluation run" value={run?.id || ''} onChange={e => setActiveRun(e.target.value)}><option value="">Select a run</option>{runs.map(r => <option key={r.id} value={r.id}>{new Date(r.created).toLocaleString()} · {r.status}</option>)}</select></div>{provider === 'cloud' && <div className="privacy-note">Cloud evaluation sends benchmark questions and retrieved source passages to your configured provider.</div>}<div className="eval-note"><CircleHelp size={17}/><p>Import and index the demo corpus first. Each run evaluates both modes (80 answers). Correctness metrics remain blank until you review the answers. Reference labels are bundled drafts for human review.</p></div>{run ? <><div className="eval-status"><span className={`dot ${run.status === 'complete' ? 'green' : ''}`}/>{run.status} · {run.result.rows.length} / 80 answers</div><div className="panel table-wrap"><table><thead><tr><th>Metric</th><th>Baseline RAG</th><th>Graph RAG</th><th>Target</th></tr></thead><tbody>{[['Recall@5 (source coverage)','recall_at_5','≥ 85%'],['Abstention accuracy','abstention_accuracy','≥ 90%'],['Answer correctness · reviewed','answer_correctness','Human review'],['Citation support · reviewed','citation_correctness','Human review'],['Median latency','p50_ms','Measure'],['95th percentile latency','p95_ms','Measure']].map(([label,key,target]) => <tr key={key}><td>{label}</td><td>{fmt(run.result.summary?.baseline?.[key], !key.includes('_ms'))}</td><td>{fmt(run.result.summary?.graph?.[key], !key.includes('_ms'))}</td><td className="muted">{target}</td></tr>)}</tbody></table></div><h2 className="section-title">Inspect & review</h2><div className="review-list">{run.result.rows.map(r => <details className="panel review-case" key={r.id+r.mode}><summary><span className="tiny-pill">{r.mode}</span><strong>{r.question}</strong><span>{r.error ? 'Error' : r.review ? 'Reviewed' : 'Needs review'}</span></summary><div><p><b>Reference:</b> {r.expected_answer}</p><p><b>Answer:</b> {r.error || r.answer}</p><div className="citation-list">{(r.citations || []).map(c => <button key={c.id} onClick={() => setSelected(c)}>[{c.number}] {c.title}</button>)}</div>{!r.error && <ReviewControls row={r} disabled={run.status === 'running'} save={(answer_correct, citations_supported) => void action(() => api(`/evaluations/${run.id}/review`, post({case_id: r.id, mode: r.mode, answer_correct, citations_supported})))}/>}</div></details>)}</div></> : <div className="large-empty"><FlaskConical size={40}/><h2>Evidence beats a good-looking demo.</h2><p>Test direct questions, paraphrases, cross-document queries, follow-ups, and evidence gaps.</p></div>}</>}

      {page === 'about' && <div className="about-grid"><section className="panel about-card"><h2>Start locally</h2><p>Install the locked Python and frontend dependencies, then run the backend and Vite. Full commands are in the project README.</p><pre>uv sync --extra voice<br/>{health?.local_backend === 'lmstudio' ? `LM Studio: load ${health.local_model} and start the server` : 'ollama pull qwen3:4b'}<br/>uv run uvicorn localvoiceai.app:app --host 127.0.0.1 --port 8017</pre><p>Speech models download the first time you enable voice. After warming all models, offline mode keeps inference local. Use headphones to reduce speaker echo.</p><div className="status-line"><span className={`dot ${health?.voice_installed ? 'green' : ''}`}/>{health?.voice_installed ? 'Speech dependencies installed' : 'Install the voice extra to enable local speech'}</div></section><section className="panel about-card"><h2>Every layer has a job</h2>{[['LangChain','Model adapters, embeddings, document splitting, and Qdrant retrieval.'],['LangGraph','Conversation checkpoints, evidence assessment, and one bounded retry.'],['RAG','Find relevant evidence and tie answers back to actual source passages.'],['Voice transport','Detect speech, stream audio, and cancel stale work when you interrupt.']].map(([name,text]) => <div className="architecture-row" key={name}><strong>{name}</strong><p>{text}</p></div>)}</section><section className="panel about-card"><h2>Honest measurements</h2><p>Retrieval scores are ranking signals, not confidence percentages. Graph mode uses hybrid rank fusion, so its scores are not directly comparable with baseline cosine similarity.</p><p>Latency depends on your hardware, selected model, and corpus. Evaluation results are measured locally. Citation support and answer correctness require human review.</p></section><section className="panel about-card"><h2>Privacy & limits</h2><p>Single-user localhost service. Documents, checkpoints, audio-playback receipts, and results stay in the data directory. Raw microphone recordings are not retained.</p><p>Cloud mode transmits relevant context only when selected. Scanned PDFs, site crawling, account-protected pages, and multi-user hosting are outside this version.</p></section></div>}
      <footer className="page-footer"><span><AudioLines size={16}/> LOCALVOICE / AI</span><span>Stay curious. Keep listening.</span><span>LangChain <span className="footer-dot">/</span> LangGraph <span className="footer-dot">/</span> RAG</span></footer>
    </main>
    <input hidden type="file" accept=".pdf,.md,.txt" ref={fileInput} onChange={e => {if(e.target.files?.[0]) void upload(e.target.files[0]); e.target.value='';}}/>
    <input hidden type="file" accept=".pdf,.md,.txt" ref={replaceInput} onChange={e => {if(e.target.files?.[0]) void upload(e.target.files[0],true); e.target.value='';}}/>
    {workspaceSettings && <WorkspaceConnection onClose={()=>setWorkspaceSettings(false)} onConnect={changeWorkspace}/>}
    {providerSettings && <ProviderSettings health={health} onClose={() => setProviderSettings(false)} onSaved={status => {setHealth(status);setNotice('API connection updated. Select API in the header to use it.');}}/>}
    {(selected || sourceDetail) && <div className="modal-backdrop" onClick={() => {setSelected(undefined);setSourceDetail(undefined);}}><section className="source-modal panel" role="dialog" aria-modal="true" aria-label="Source evidence" onClick={e => e.stopPropagation()}><button className="modal-close" aria-label="Close source" onClick={() => {setSelected(undefined);setSourceDetail(undefined);}}><X size={21}/></button><div className="eyebrow">SOURCE EVIDENCE</div><h2>{selected?.title || sourceDetail?.title}</h2>{selected ? <><p className="muted">Version {selected.version}{selected.page ? ` · Page ${selected.page}` : ` · ${selected.section || 'Text passage'}`}</p><pre>{selected.text}</pre>{selected.url && <a href={selected.url} target="_blank" rel="noreferrer">Open original page <ExternalLink size={14}/></a>}<p className="mono muted">Passage {selected.id}</p></> : sourceDetail?.passages?.map(p => <div className="full-passage" key={p.id}><small>{p.metadata.page ? `PAGE ${p.metadata.page}` : p.metadata.section || 'PASSAGE'}</small><pre>{p.text}</pre></div>)}<button className="secondary" onClick={() => {setSelected(undefined);setSourceDetail(undefined);}}>Done <Check size={15}/></button></section></div>}
  </div>;
}
