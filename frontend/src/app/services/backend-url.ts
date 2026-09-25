declare global {
  interface Window {
    __QUOTE_PLOT_CONFIG__?: {
      backendOrigin?: string;
      sepoliaRpcUrl?: string;
    };
  }
}

function backendOrigin(): string {
  return (window.__QUOTE_PLOT_CONFIG__?.backendOrigin ?? '').replace(/\/+$/, '');
}

export function backendApiUrl(path: string): string {
  return `${backendOrigin()}${path}`;
}

export function backendWebSocketUrl(path: string): string {
  const origin = backendOrigin();
  if (!origin) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${path}`;
  }

  const endpoint = new URL(origin);
  endpoint.protocol = endpoint.protocol === 'https:' ? 'wss:' : 'ws:';
  endpoint.pathname = path;
  endpoint.search = '';
  endpoint.hash = '';
  return endpoint.toString();
}
