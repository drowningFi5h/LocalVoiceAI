import {useEffect, useRef, useState} from 'react';
import {X, Laptop} from 'lucide-react';
import {checkWorkspace, workspaceAddress, hosted} from './api';

export default function WorkspaceConnection({onClose, onConnect}: {onClose:()=>void; onConnect:(address:string, token:string)=>void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [address,setAddress] = useState(workspaceAddress() || 'http://127.0.0.1:8017');
  const [token,setToken] = useState('');
  const [pending,setPending] = useState(false);
  const [error,setError] = useState('');
  useEffect(()=>{dialog.current?.showModal();},[]);
  async function connect() {
    setPending(true);setError('');
    try {await checkWorkspace(address,token);onConnect(address,token);}
    catch(e) {setError(e instanceof TypeError ? 'Cannot reach the local server. Start it, allow this site’s local network access, and check the paired site address. If your browser blocks the connection, open the local app instead.' : String(e));}
    finally {setPending(false);}
  }
  return <dialog ref={dialog} className="provider-dialog" aria-labelledby="workspace-title" onCancel={e=>{e.preventDefault();if(!pending)onClose();}}>
    <button className="modal-close" disabled={pending} aria-label="Close workspace connection" onClick={onClose}><X size={20}/></button>
    <div className="settings-icon"><Laptop size={24}/></div><span className="section-label">LOCAL WORKSPACE</span>
    <h2 id="workspace-title">Your computer. Connected.</h2>
    <p className="settings-intro">This page connects directly to your local server. Keep it running while you use the studio.</p>
    <p className="key-note">Use the LocalVoiceAI backend port (usually 8017). LM Studio’s model port (1234) is configured in the backend.</p>
    <form onSubmit={e=>{e.preventDefault();void connect();}}><fieldset disabled={pending}>
      <label>Local backend address<input required value={address} onChange={e=>setAddress(e.target.value)} /></label>
      {hosted && <label>Pairing token<input required type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} pattern="[A-Za-z0-9_-]{32,}" /></label>}
      {hosted && <details className="connection-details"><summary>Pair this site</summary>
        <p>Run these commands in your LocalVoiceAI folder, then paste the generated token above.</p>
        <pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{`.venv/Scripts/python.exe scripts/pair_workspace.py --origin ${location.origin}`}</pre>
        <pre>powershell -File scripts/start.ps1 -Hosted</pre>
        <p>Restart any running backend after pairing. Only pair a site you trust: it can access your local library and conversations. The token stays in this tab’s memory and clears on reload. API mode still sends context to your chosen provider.</p>
      </details>}
      {error && <p role="alert" className="settings-error">{error}</p>}
      <button className="primary" type="submit">{pending ? 'Connecting…' : 'Connect workspace'}</button>
      <a className="secondary" href="http://127.0.0.1:8017/" target="_blank" rel="noreferrer">Open local app</a>
    </fieldset></form>
  </dialog>;
}
