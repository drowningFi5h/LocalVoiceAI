import { Cloud, Cpu, ShieldCheck, ArrowRight, Globe2, Info } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import type { Health, Provider } from './types';

export function ProviderSwitch({ provider, available, locked, onChange }: {
  provider: Provider; available: boolean; locked: boolean; onChange: (provider: Provider) => void;
}) {
  const reduced = useReducedMotion();
  const remote = provider === 'cloud';
  const disabled = locked || (!remote && !available);
  return <div className="provider-switch-wrap">
    <button type="button" className="provider-switch" role="switch" aria-checked={remote}
      aria-label="Use API instead of local generation" aria-describedby="provider-switch-help" disabled={disabled}
      title={locked ? 'End voice or stop the response before switching' : !available ? 'API is unavailable in offline mode or without credentials' : 'Switch generation provider'}
      onClick={() => onChange(remote ? 'local' : 'cloud')}>
      <motion.span className="provider-switch-thumb" initial={false} animate={{left:remote ? '50%' : '4px'}}
        transition={reduced ? {duration:0} : {type:'spring', stiffness:330, damping:29}}/>
      <span className={!remote ? 'is-selected' : ''}><Cpu size={15}/> Local</span>
      <span className={remote ? 'is-selected' : ''}><Cloud size={15}/> API</span>
    </button>
    <span id="provider-switch-help" className="sr-only">{locked ? 'End voice or stop the current response before switching.' : !available ? 'API credentials are not configured, or offline mode is enabled.' : 'Local runs on this computer. API sends questions and relevant context to the configured cloud provider.'}</span>
  </div>;
}

export function ProviderContext({provider, health, ready}: {provider:Provider; health?:Health; ready:boolean | null}) {
  const remote = provider === 'cloud';
  const destination = health?.cloud_provider || (health?.cloud_backend === 'gemini' ? 'Google' : 'your configured provider');
  return <section className="provider-context" aria-label="Generation provider">
    <div className="provider-emblem" aria-hidden="true">{remote ? <Cloud size={24}/> : <Cpu size={24}/>}</div>
    <div className="provider-context-copy"><span className="section-label">{remote ? health?.cloud_provider || 'API' : 'LOCAL / ON THIS DEVICE'}</span><p>{remote ? 'A different engine. The same knowledge.' : 'Your machine. Your model. Your knowledge.'}</p></div>
    <div className="provider-route"><span className="provider-model">{remote ? health?.cloud_model || 'Gemini' : health?.local_model || 'Local model'}</span>
      <span className="provider-route-status">{remote ? <Globe2 size={12}/> : <ShieldCheck size={12}/>}{remote ? 'API configured' : ready ? 'Local model ready' : ready === false ? 'Local model unavailable' : 'Checking local model'}<ArrowRight size={12}/>{remote ? 'Audio stays local' : 'No cloud generation'}</span></div>
    <details className="hover-details provider-help"><summary aria-label="Provider privacy and processing details"><Info size={16}/></summary><p className="provider-disclosure">{remote ? `Questions, conversation context and retrieved passages go to ${destination}. Speech and indexing stay on your device.` : 'Generation, speech and indexing run on your device. Switch to API when you want a cloud model to answer.'}</p></details>
    {remote && <span className="cloud-destination">Context sent to {destination}</span>}
  </section>;
}
