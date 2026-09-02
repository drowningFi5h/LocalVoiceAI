import { useEffect, useRef, useState } from 'react';
import { animate, createScope, stagger } from 'animejs';
import { motion, useReducedMotion, type HTMLMotionProps } from 'motion/react';
import { ArrowDown, ArrowUpRight, Pause, Play, Mic, LoaderCircle } from 'lucide-react';
import Resonance from './Resonance';

// Adapted from Animate UI's button primitive. See THIRD_PARTY_NOTICES.md.
// The unused Slot branch is omitted; reduced-motion support is added.
export function MotionButton({ hoverScale = 1.025, tapScale = .97, ...props }:
  HTMLMotionProps<'button'> & { hoverScale?: number; tapScale?: number }) {
  const reduced = useReducedMotion();
  return <motion.button whileHover={reduced ? undefined : { scale: hoverScale }}
    whileTap={reduced ? undefined : { scale: tapScale }} {...props}/>;
}

type HeroProps = { provider: 'local' | 'cloud'; onEnter: () => void; onVoice: () => void; voice: 'off' | 'loading' | 'on'; connected: boolean; energy: number };
export function StudioHero({ provider, onEnter, onVoice, voice, connected, energy }: HeroProps) {
  const root = useRef<HTMLElement>(null);
  const [paused, setPaused] = useState(false);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (reduced) return;
    const scope = createScope({ root }).add(() => {
      animate('.hero-reveal', { y: [22, 0], opacity: [0, 1], delay: stagger(110), duration: 1000, ease: 'outExpo' });
    });
    return () => scope.revert();
  }, [reduced]);
  return <section className="studio-hero" ref={root} aria-label="LocalVoice listening studio">
    <div className="hero-content">
      <div className="hero-copy"><h1 className="hero-reveal">Localvoice.</h1><p className="hero-promise hero-reveal">{provider === 'cloud' ? 'Your knowledge, connected.' : 'Your knowledge, in conversation.'}</p>
        <div className="hero-description hero-reveal"><p>Talk to your documents. Hear the answer.<br/>Follow every word back to its source.</p></div>
        <div className="hero-actions hero-reveal"><MotionButton className="hero-cta" onClick={onEnter}>Open workspace <span><ArrowDown size={19}/></span></MotionButton><MotionButton className="hero-voice" disabled={!connected || voice === 'loading'} onClick={onVoice}>{voice === 'loading' ? <LoaderCircle className="spin" size={15}/> : <Mic size={15}/>} {voice === 'on' ? 'End voice session' : voice === 'loading' ? 'Preparing voice…' : 'Start speaking'}</MotionButton></div>
      </div>
      <div className="signal-art"><Resonance paused={paused || !!reduced} energy={energy}/></div>
    </div>
    <div className="hero-bottom"><button disabled={!!reduced} title={reduced ? 'Motion reduced by system preference' : undefined} className="motion-toggle" aria-label={paused ? 'Resume artwork animation' : 'Pause artwork animation'} onClick={() => setPaused(!paused)}>{paused || reduced ? <Play size={12}/> : <Pause size={12}/>}</button></div>
  </section>;
}
