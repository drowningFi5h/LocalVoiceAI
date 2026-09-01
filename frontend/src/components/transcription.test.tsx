import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { Transcription, TranscriptionSegment } from './transcription';

describe('transcription states', () => {
  it('highlights the current sentence, filters empty text, and keeps static text out of the tab order', () => {
    const markup = renderToStaticMarkup(<Transcription currentTime={2.5} segments={[
      {text:'First.', startSecond:0, endSecond:2}, {text:'  ',startSecond:2,endSecond:2},
      {text:'Second.',startSecond:2,endSecond:4}, {text:'Third.',startSecond:4,endSecond:6},
    ]}>{(segment,index) => <TranscriptionSegment key={index} segment={segment} index={index}/>}</Transcription>);
    expect(markup).toContain('data-active="true" data-past="false" data-index="1" aria-current="true">Second.');
    expect(markup).toContain('data-active="false" data-past="true" data-index="0">First.');
    expect(markup).not.toContain('<button');
    expect(markup.match(/data-slot="transcription-segment"/g)).toHaveLength(3);
  });
});
