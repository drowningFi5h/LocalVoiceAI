import { afterEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { AudioEngine } from './audio';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('transcript playback clock', () => {
  it('uses decoded sentence durations and stops publishing on interruption', async () => {
    vi.useFakeTimers();
    const nodes: any[] = [];
    const context = {currentTime:10, destination:{}, decodeAudioData:async () => ({duration:2}),
      createBufferSource: () => { const node = {connect:vi.fn(), disconnect:vi.fn(), start:vi.fn(), stop:vi.fn(), onended:null}; nodes.push(node); return node; }};
    const engine = new AudioEngine();
    engine.context = context as unknown as AudioContext;
    const update = vi.fn(), played = vi.fn();
    engine.onPlayback = update;
    engine.enqueue('AA==', played, {turnId:'one', text:'First sentence.'});
    engine.enqueue('AA==', played, {turnId:'one', text:'Second sentence.'});
    await engine.tail;
    const segments = update.mock.lastCall![0].segments;
    expect(segments).toEqual([{text:'First sentence.', startSecond:0, endSecond:2}, {text:'Second sentence.', startSecond:2, endSecond:4}]);
    context.currentTime = 12.52;
    vi.advanceTimersByTime(75);
    expect(update.mock.lastCall![0].currentTime).toBeCloseTo(2.5);
    expect(update.mock.lastCall![0].speaking).toBe(true);
    engine.stopPlayback();
    expect(update.mock.lastCall![0]).toMatchObject({speaking:false, interrupted:true});
    const count = update.mock.calls.length;
    vi.advanceTimersByTime(1000);
    expect(update).toHaveBeenCalledTimes(count);
    expect(played).not.toHaveBeenCalled();
    expect(nodes.every(n => n.onended === null)).toBe(true);
    engine.enqueue('AA==', played, {turnId:'two', text:'New turn.'});
    await engine.tail;
    expect(update.mock.lastCall![0].segments).toEqual([{text:'New turn.', startSecond:0, endSecond:2}]);
    engine.stopPlayback();
  });
});

describe('audio cancellation', () => {
  it('drops a stale decode when playback is interrupted', async () => {
    let resolve!: (value: unknown) => void;
    const create = vi.fn();
    const engine = new AudioEngine();
    engine.context = {decodeAudioData: () => new Promise(r => {resolve = r;}), createBufferSource: create} as unknown as AudioContext;
    engine.enqueue('AA==', vi.fn());
    await Promise.resolve();
    const old = engine.tail;
    engine.stopPlayback();
    resolve({duration: 1});
    await old;
    expect(create).not.toHaveBeenCalled();
  });

  it('stops queued sources without acknowledging unheard audio', () => {
    const engine = new AudioEngine();
    const acknowledged = vi.fn();
    const stop = vi.fn();
    const node = {onended: acknowledged, stop} as unknown as AudioBufferSourceNode;
    engine.playing.add(node);
    engine.stopPlayback();
    expect(stop).toHaveBeenCalledOnce();
    expect(node.onended).toBeNull();
    expect(acknowledged).not.toHaveBeenCalled();
    expect(engine.playing.size).toBe(0);
  });
});

describe('AudioWorklet framing', () => {
  for (const rate of [44100, 48000]) it(`resamples ${rate} Hz to bounded 16 kHz PCM16 frames`, () => {
    let Processor: any;
    const frames: {pcm: ArrayBuffer; energy: number; interrupt: boolean}[] = [];
    const sandbox = {
      sampleRate: rate,
      AudioWorkletProcessor: class {port = {postMessage: (frame: any) => frames.push(frame)};},
      registerProcessor: (_name: string, type: unknown) => {Processor = type;},
    };
    vm.runInNewContext(readFileSync(new URL('../public/audio-worklet.js', import.meta.url), 'utf8'), sandbox);
    const processor = new Processor();
    for (let n = 0; n < rate; n += 128) processor.process([[new Float32Array(Math.min(128, rate - n)).fill(.2)]]);
    expect(frames.length).toBe(31); // floor(16,000 / 512)
    expect(frames.every(f => f.pcm.byteLength === 1024)).toBe(true);
    expect(frames[2].interrupt).toBe(true);
    expect(new Int16Array(frames[0].pcm)[0]).toBeGreaterThan(6500);
    expect(processor.buffer.length).toBeLessThan(4);
  });
});
