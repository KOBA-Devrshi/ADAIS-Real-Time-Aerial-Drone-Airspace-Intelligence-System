export class AnalysisSocketClient {
  private ws: WebSocket | null = null;
  private pingTimer: number | null = null;

  connect(sessionId: string, onMessage: (data: any) => void, onStatus?: (connected: boolean) => void) {
    this.disconnect();
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/ws/analysis/${sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      onStatus?.(true);
      this.pingTimer = window.setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('PING');
        }
      }, 15000);
    };

    this.ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data);
        onMessage(parsed);
      } catch {
        // Ignore malformed packets
      }
    };

    this.ws.onclose = () => {
      onStatus?.(false);
      if (this.pingTimer) clearInterval(this.pingTimer);
    };
  }

  disconnect() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
