import { useEffect, useRef } from "react";

interface UseSSEOptions<T> {
  url: string;
  onMessage: (data: T) => void;
  onError?: (err: Event) => void;
  enabled?: boolean;
}

/**
 * Generic EventSource hook with auto-reconnect.
 * Reconnects with exponential backoff on connection error.
 */
export function useSSE<T>({ url, onMessage, onError, enabled = true }: UseSSEOptions<T>) {
  const esRef = useRef<EventSource | null>(null);
  const backoffRef = useRef(1000);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const es = new EventSource(url);
      esRef.current = es;

      es.onmessage = (event) => {
        backoffRef.current = 1000; // reset backoff on successful message
        try {
          const data = JSON.parse(event.data) as T;
          onMessage(data);
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = (err) => {
        onError?.(err);
        es.close();
        esRef.current = null;
        if (!cancelled) {
          // Reconnect with exponential backoff (max 30s)
          const delay = Math.min(backoffRef.current, 30_000);
          backoffRef.current = Math.min(backoffRef.current * 2, 30_000);
          setTimeout(connect, delay);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      esRef.current?.close();
      esRef.current = null;
    };
  }, [url, enabled]); // eslint-disable-line react-hooks/exhaustive-deps
}
