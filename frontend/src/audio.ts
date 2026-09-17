export type PlaybackSegment = {text: string; startSecond: number; endSecond: number};
export type PlaybackSnapshot = {turnId: string | null; segments: PlaybackSegment[]; currentTime: number; speaking: boolean; interrupted: boolean};
export const emptyPlayback = (): PlaybackSnapshot => ({turnId:null, segments:[], currentTime:-1, speaking:false, interrupted:false});

export class AudioEngine {
  context?: AudioContext;
  stream?: MediaStream;
  node?: AudioWorkletNode;
  source?: MediaStreamAudioSourceNode;
  playing = new Set<AudioBufferSourceNode>();
  epoch = 0;
  tail: Promise<void> = Promise.resolve();
  nextTime = 0;
  onPlayback?: (snapshot: PlaybackSnapshot) => void;
  private playback = emptyPlayback();
  private playbackOrigin = 0;
  private playbackTimer?: ReturnType<typeof setInterval>;

  private publishPlayback(interrupted = false) {
    const last = this.playback.segments.at(-1);
    if (!last || !this.context) return;
    const time = Math.min(last.endSecond, this.context.currentTime - this.playbackOrigin);
    this.playback = {...this.playback, currentTime:time, interrupted,
      speaking: !interrupted && this.playing.size > 0 && this.playback.segments.some(s => time >= s.startSecond && time < s.endSecond)};
    this.onPlayback?.(this.playback);
  }

  async prepare() {
    this.context ??= new AudioContext();
    await this.context.resume();
  }

  async capture(onFrame: (pcm: ArrayBuffer, energy: number, interrupt: boolean) => void) {
    await this.prepare();
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: {
      channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true,
    }});
    await this.context!.audioWorklet.addModule('/audio-worklet.js');
    this.source = this.context!.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.context!, 'capture');
    this.node.port.onmessage = e => onFrame(e.data.pcm, e.data.energy, e.data.interrupt);
    this.source.connect(this.node);
    // The processor outputs silence; connection keeps capture active without microphone feedback.
    this.node.connect(this.context!.destination);
  }

  enqueue(wav: string, onPlayed: () => void, transcript?: {turnId: string; text: string}) {
    const epoch = this.epoch;
    this.tail = this.tail.then(async () => {
      if (epoch !== this.epoch || !this.context) return;
      const data = Uint8Array.from(atob(wav), c => c.charCodeAt(0));
      const buffer = await this.context.decodeAudioData(data.buffer);
      if (epoch !== this.epoch) return;
      const node = this.context.createBufferSource();
      node.buffer = buffer;
      node.connect(this.context.destination);
      this.playing.add(node);
      const start = Math.max(this.context.currentTime + .02, this.nextTime);
      this.nextTime = start + buffer.duration;
      if (transcript) {
        if (this.playback.turnId !== transcript.turnId) {
          this.playback = {...emptyPlayback(), turnId:transcript.turnId};
          this.playbackOrigin = start;
        }
        this.playback = {...this.playback, segments:[...this.playback.segments, {
          text:transcript.text, startSecond:start - this.playbackOrigin, endSecond:this.nextTime - this.playbackOrigin,
        }]};
        this.publishPlayback();
        if (this.onPlayback && !this.playbackTimer) this.playbackTimer = setInterval(() => this.publishPlayback(), 75);
      }
      node.onended = () => {
        this.playing.delete(node); node.disconnect();
        if (epoch === this.epoch) { onPlayed(); this.publishPlayback(); }
        if (!this.playing.size) { clearInterval(this.playbackTimer); this.playbackTimer = undefined; }
      };
      node.start(start);
    }).catch(() => { /* A cancelled decode or closed audio context must not block later turns. */ });
  }

  stopPlayback() {
    this.publishPlayback(this.playback.interrupted || this.playing.size > 0);
    clearInterval(this.playbackTimer); this.playbackTimer = undefined;
    this.epoch++;
    this.nextTime = 0;
    for (const node of this.playing) { node.onended = null; try { node.stop(); } catch { /* ended */ } }
    this.playing.clear();
    this.tail = Promise.resolve();
  }

  stopCapture() {
    this.node?.disconnect(); this.source?.disconnect();
    this.stream?.getTracks().forEach(track => track.stop());
    this.node = undefined; this.stream = undefined;
  }

  close() { this.stopPlayback(); this.stopCapture(); void this.context?.close(); this.context = undefined; }
}
