// Central API module - supports local Vite proxy and production API base URL
const BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchPresets() {
  const r = await fetch(`${BASE}/api/presets`);
  return r.json();
}

export async function fetchFiles() {
  const r = await fetch(`${BASE}/api/files`);
  return r.json();
}

export async function fetchDecompose(filename) {
  const r = await fetch(`${BASE}/api/decompose?file=${encodeURIComponent(filename)}`);
  if (!r.ok) throw new Error(`Decompose failed: ${r.status}`);
  return r.json();
}

export function previewUrl(filename) {
  return `${BASE}/api/preview/${encodeURIComponent(filename)}`;
}

export async function runPipeline(payload) {
  const r = await fetch(`${BASE}/api/run-pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok || !data.success) throw new Error(data.error || data.logs || "Pipeline failed");
  return data;
}

export function openPipelineStream(payload, onLog, onComplete, onError) {
  const ctrl = new AbortController();
  fetch(`${BASE}/api/run-pipeline-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (response) => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(part.slice(6));
            if (msg.type === "log") onLog(msg.text);
            else if (msg.type === "complete") onComplete(msg.data);
            else if (msg.type === "error") onError(msg.text);
          } catch (_) {}
        }
      }
    })
    .catch((e) => {
      if (e.name !== "AbortError") onError(e.message);
    });

  return () => ctrl.abort();
}
