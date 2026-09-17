import {beforeEach, describe, expect, it, vi} from 'vitest';

beforeEach(()=>{
  vi.resetModules();vi.unstubAllGlobals();
  vi.stubGlobal('location', {hostname:'studio.vercel.app',origin:'https://studio.vercel.app'});
});
describe('local workspace transport',()=>{
  it('does not contact a backend before explicit connection',async()=>{
    const fetch = vi.fn();vi.stubGlobal('fetch',fetch);
    const api = await import('./api');
    expect(api.workspaceReady()).toBe(false);
    await expect(api.api('/sources')).rejects.toThrow('Connect');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('restricts targets to loopback origins',async()=>{
    const {validateWorkspace} = await import('./api');
    for(const address of ['https://example.com','http://127.0.0.1:8017/path','http://user:pass@localhost','http://localhost?token=a'])
      expect(()=>validateWorkspace(address)).toThrow();
    expect(validateWorkspace('http://localhost:8017/')).toBe('http://localhost:8017');
  });
  it('sends authorization without changing multipart headers and clears on disconnect',async()=>{
    const fetch = vi.fn().mockResolvedValue({ok:true,json:async()=>[]});vi.stubGlobal('fetch',fetch);
    const api = await import('./api');
    api.configureWorkspace('http://127.0.0.1:8017','a'.repeat(43));
    await api.api('/sources/upload',{method:'POST',body:new FormData()});
    const [url,options] = fetch.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8017/api/sources/upload');
    expect(options.headers.get('Authorization')).toBe('Bearer '+'a'.repeat(43));
    expect(options.headers.has('Content-Type')).toBe(false);
    expect(options.redirect).toBe('error');
    api.configureWorkspace('','');
    expect(api.workspaceReady()).toBe(false);
  });
  it('derives WebSocket scheme from the backend and keeps tokens out of URLs',async()=>{
    const socket = vi.fn(function(_url: URL, _protocols: string[]) {});vi.stubGlobal('WebSocket',socket);
    const api = await import('./api');
    api.configureWorkspace('http://127.0.0.1:8017','a'.repeat(43));
    api.workspaceSocket('session');
    expect(String(socket.mock.calls[0][0])).toBe('ws://127.0.0.1:8017/api/ws/session');
    expect(socket.mock.calls[0][1]).toEqual(['lva-pair.'+'a'.repeat(43)]);
  });
});
