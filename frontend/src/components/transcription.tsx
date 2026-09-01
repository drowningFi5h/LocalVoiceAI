// Adapted from Vercel AI Elements' transcription component.
// Copyright 2023 Vercel, Inc. Apache-2.0. See AI_ELEMENTS_LICENSE.txt.
// Uses controlled playback time, local types and CSS; static segments are spans.
import { createContext, useContext, type ComponentProps, type ReactNode } from 'react';

export type TranscriptSegment = { text: string; startSecond: number; endSecond: number };
const Context = createContext<{currentTime: number; onSeek?: (time: number) => void} | null>(null);

export function Transcription({ segments, currentTime = -1, onSeek, children, ...props }:
  Omit<ComponentProps<'div'>, 'children'> & { segments: TranscriptSegment[]; currentTime?: number;
    onSeek?: (time: number) => void; children: (segment: TranscriptSegment, index: number) => ReactNode }) {
  return <Context.Provider value={{currentTime, onSeek}}><div data-slot="transcription" {...props}>
    {segments.filter(segment => segment.text.trim()).map(children)}
  </div></Context.Provider>;
}

export function TranscriptionSegment({ segment, index }: {segment: TranscriptSegment; index: number}) {
  const context = useContext(Context);
  if (!context) throw new Error('TranscriptionSegment must be rendered inside Transcription');
  const active = context.currentTime >= segment.startSecond && context.currentTime < segment.endSecond;
  const past = context.currentTime >= segment.endSecond;
  const attributes = {'data-slot': 'transcription-segment', 'data-active': active, 'data-past': past,
    'data-index': index, 'aria-current': active ? 'true' as const : undefined};
  return context.onSeek ? <button type="button" {...attributes} onClick={() => context.onSeek?.(segment.startSecond)}>{segment.text}</button>
    : <span {...attributes}>{segment.text}</span>;
}
