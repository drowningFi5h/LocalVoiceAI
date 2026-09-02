import { AudioLines, Mic, MicOff, Square, LoaderCircle, ArrowUpRight } from 'lucide-react';
import { MotionButton } from './Studio';
import { Transcription, TranscriptionSegment } from './components/transcription';
import type { PlaybackSnapshot } from './audio';

type Props = { voice: 'off' | 'loading' | 'on'; connected: boolean; busy: boolean; energy: number;
  question?: string; playback: PlaybackSnapshot; onVoice: () => void; onStop: () => void; onType: () => void };

export default function VoiceWorkspace({voice, connected, busy, energy, question, playback, onVoice, onStop, onType}: Props) {
  const speaking = playback.speaking;
  const label = !connected ? 'Disconnected' : voice === 'loading' ? 'Preparing voice' : speaking ? 'Speaking'
    : busy ? 'Preparing your answer' : voice === 'on' ? 'Listening' : 'Ready when you are';
  return <section className={`voice-workspace ${voice === 'on' ? 'is-listening' : ''}`} aria-label="Voice conversation">
    <div className="voice-identity"><span className="section-label">VOICE CONVERSATION</span>
      <h2 aria-live="polite" aria-atomic="true">{label}</h2><p>{voice === 'off' ? 'Talk things through. Explore your ideas and sources.' : voice === 'loading' ? 'Loading the local speech models.' : 'Speak naturally. Interrupt at any time.'}</p>
      <button className="voice-type-link" onClick={onType}>Prefer to type? <ArrowUpRight size={13}/></button>
    </div>
    <div className="voice-instrument">
      <div className="input-meter" aria-hidden="true">{Array.from({length:31},(_,i) => <i key={i} style={{height: voice === 'on' ? `${5 + Math.min(energy * 450, 65) * (.3 + .7 * Math.abs(Math.cos(i * .8)))}px` : '3px'}}/>)}</div>
      <MotionButton className={`voice-main-button ${voice === 'on' ? 'active' : ''}`} disabled={!connected || voice === 'loading'} onClick={onVoice}
        aria-label={voice === 'on' ? 'End voice conversation' : 'Start voice conversation'}>
        {voice === 'loading' ? <LoaderCircle size={25} className="spin"/> : voice === 'on' ? <MicOff size={25}/> : <Mic size={25}/>}</MotionButton>
      <span className="voice-instrument-caption">{voice === 'on' ? 'MICROPHONE ON' : 'TAP TO TALK'}</span>
    </div>
    <div className="voice-transcript"><div className="transcript-heading"><span className="section-label">{playback.segments.length ? 'SPOKEN RESPONSE' : 'YOUR TRANSCRIPT'}</span>
      {(busy || speaking) && <button onClick={onStop} aria-label="Stop response"><Square size={12}/> Stop</button>}</div>
      {playback.segments.length ? <><Transcription segments={playback.segments} currentTime={playback.currentTime}>
        {(segment,index) => <TranscriptionSegment key={index} segment={segment} index={index}/>}</Transcription>
        <div className="transcript-caption"><AudioLines size={13}/>{speaking ? 'Playing · sentence sync' : playback.interrupted ? 'Playback stopped' : playback.currentTime >= (playback.segments.at(-1)?.endSecond ?? Infinity) ? 'Playback complete' : 'Audio queued'}<span>{Math.max(0,playback.currentTime).toFixed(1)}s</span></div></>
        : <p className={question ? 'transcript-question' : 'transcript-placeholder'}>{question || 'Your words will appear here after you finish speaking.'}</p>}
    </div>
  </section>;
}
