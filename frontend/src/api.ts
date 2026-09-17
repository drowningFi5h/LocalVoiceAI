export const hosted = !['localhost', '127.0.0.1'].includes(location.hostname);
let backend = hosted ? '' : location.origin;
let pairingToken = '';
let revision = 0;
export const workspaceReady = () => !!backend;
export const workspaceAddress = () => backend;
export const sessionKey = () => 'lva-session:' + backend;
export function validateWorkspace(address: string): string {
  const url = new URL(address);
  if (!['http:', 'https:'].includes(url.protocol) || !['localhost', '127.0.0.1'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash)
    throw new Error('Use a localhost address such as http://127.0.0.1:8017');
  return url.origin;
}
export function configureWorkspace(address: string, token: string) {
  backend = address ? validateWorkspace(address) : '';
  pairingToken = token.trim(); revision++;
}
export async function checkWorkspace(address: string, token: string) {
  const response = await fetch(validateWorkspace(address) + '/api/health', {
    headers: token.trim() ? {Authorization: 'Bearer ' + token.trim()} : {}, credentials: 'omit', redirect: 'error',
    signal: AbortSignal.timeout(10000), targetAddressSpace: 'loopback',
  } as RequestInit);
  if (!response.ok) throw new Error(response.status === 401 ? 'Pairing token rejected. Check the token and restart the local server after pairing.' : `Local server refused the connection (${response.status}).`);
  const health = await response.json();
  if (health.workspace_protocol !== 1) throw new Error('Update and restart your local LocalVoiceAI backend first.');
}
export function workspaceSocket(id: string) {
  const url = new URL('/api/ws/' + encodeURIComponent(id), backend);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return new WebSocket(url, pairingToken ? ['lva-pair.' + pairingToken] : []);
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (!backend) throw new Error('Connect your local workspace first.');
  const current = revision;
  const headers = new Headers(init?.headers);
  if (pairingToken) headers.set('Authorization', 'Bearer ' + pairingToken);
  const response = await fetch(backend + '/api' + path, {...init, headers, credentials: 'omit', redirect: 'error',
    targetAddressSpace: 'loopback'} as RequestInit);
  if (current !== revision) throw new Error('Workspace changed.');
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  const body = await response.json();
  if (current !== revision) throw new Error('Workspace changed.');
  return body;
}
export const post = (body?: unknown): RequestInit => ({method: 'POST',
  ...(body === undefined ? {} : {headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})});
