// Resample the device's native rate to mono 16 kHz, then frame as 512 PCM16 samples.
class Capture extends AudioWorkletProcessor {
  constructor() { super(); this.buffer = []; this.position = 0; this.frame = []; this.hot = 0; }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) return true;
    this.buffer.push(...input);
    const step = sampleRate / 16000;
    while (this.position + 1 < this.buffer.length) {
      const i = Math.floor(this.position), fraction = this.position - i;
      this.frame.push(this.buffer[i] * (1 - fraction) + this.buffer[i + 1] * fraction);
      this.position += step;
      if (this.frame.length === 512) {
        const energy = Math.sqrt(this.frame.reduce((sum, v) => sum + v * v, 0) / 512);
        this.hot = energy > 0.035 ? this.hot + 1 : 0;
        const pcm = new Int16Array(this.frame.map(v => Math.max(-32768, Math.min(32767, v * 32768))));
        this.port.postMessage({ pcm: pcm.buffer, energy, interrupt: this.hot === 3 }, [pcm.buffer]);
        this.frame = [];
      }
    }
    const consumed = Math.floor(this.position);
    this.buffer.splice(0, consumed); this.position -= consumed;
    return true;
  }
}
registerProcessor('capture', Capture);
