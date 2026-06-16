import { useRef, useState } from "react";
import { uploadCsv } from "../api";

export default function Upload({ onUploaded }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  function pick(f) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setMsg({ type: "err", text: "Please choose a .csv file." });
      return;
    }
    setMsg(null);
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await uploadCsv(file);
      setMsg({ type: "ok", text: `Job #${res.job_id} queued for processing.` });
      setFile(null);
      onUploaded?.(res.job_id);
    } catch (e) {
      setMsg({ type: "err", text: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 10 }}>Step 01 — Upload</div>
      <h2>Upload transactions</h2>
      <p className="sub">
        Drop a raw <code>transactions.csv</code> — cleaned, classified &amp;
        scored asynchronously.
      </p>

      {msg && <div className={`toast ${msg.type}`}>{msg.text}</div>}

      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        style={{ marginTop: 18 }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          pick(e.dataTransfer.files?.[0]);
        }}
      >
        <strong>Click to browse</strong> or drag &amp; drop
        <p>CSV up to a few thousand rows</p>
        {file && <div className="filename">📄 {file.name}</div>}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        hidden
        onChange={(e) => pick(e.target.files?.[0])}
      />

      <div style={{ marginTop: 18 }}>
        <button className="btn" disabled={!file || busy} onClick={submit}>
          {busy ? <span className="spinner" /> : null}
          {busy ? "Uploading…" : "Process file"}
        </button>
      </div>
    </div>
  );
}
