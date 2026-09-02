import { useState } from 'react';
import type { EvalRow } from './types';

export default function ReviewControls({ row, disabled, save }: {
  row: EvalRow;
  disabled: boolean;
  save: (answerCorrect: boolean, citationsSupported: boolean) => void;
}) {
  const [answer, setAnswer] = useState(row.review ? String(row.review.answer_correct) : '');
  const [citations, setCitations] = useState(row.review ? String(row.review.citations_supported) : '');
  const hasCitations = row.citations.length > 0;
  return <div className="review-actions">
    <label>Answer quality
      <select aria-label={`Answer quality ${row.id} ${row.mode}`} value={answer}
        disabled={disabled} onChange={event => setAnswer(event.target.value)}>
        <option value="">Not reviewed</option><option value="true">Correct</option><option value="false">Incorrect</option>
      </select>
    </label>
    {hasCitations && <label>Cited claims
      <select aria-label={`Citation support ${row.id} ${row.mode}`} value={citations}
        disabled={disabled} onChange={event => setCitations(event.target.value)}>
        <option value="">Not reviewed</option><option value="true">All supported</option><option value="false">Not all supported</option>
      </select>
    </label>}
    <button className="secondary" disabled={disabled || !answer || (hasCitations && !citations)}
      onClick={() => save(answer === 'true', citations === 'true')}>Save review</button>
  </div>;
}
