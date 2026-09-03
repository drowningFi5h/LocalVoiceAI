import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { ProviderSwitch, ProviderContext } from './ProviderSwitch';

describe('provider selection', () => {
  it('exposes API mode as a checked, locked switch during active work', () => {
    const markup = renderToStaticMarkup(<ProviderSwitch provider="cloud" available locked onChange={() => {}}/>);
    expect(markup).toContain('role="switch"');
    expect(markup).toContain('aria-checked="true"');
    expect(markup).toContain('disabled=""');
  });
  it('keeps local selectable state and explains unavailable credentials', () => {
    const markup = renderToStaticMarkup(<ProviderSwitch provider="local" available={false} locked={false} onChange={() => {}}/>);
    expect(markup).toContain('aria-checked="false"');
    expect(markup).toContain('disabled=""');
    expect(markup).toContain('API credentials are not configured');
  });
  it('discloses the actual cloud destination without claiming local generation', () => {
    const markup = renderToStaticMarkup(<ProviderContext provider="cloud" ready health={{local_model:'local',cloud_model:'gemini-flash-latest',cloud_backend:'gemini',cloud_available:true,voice_installed:true,offline:false}}/>);
    expect(markup).toContain('passages go to Google');
    expect(markup).toContain('Audio stays local');
    expect(markup).not.toContain('No cloud generation');
  });
});
