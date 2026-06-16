import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { listJobs } from "../api";

const FILTERS = ["all", "pending", "processing", "completed", "failed"];

function fmt(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function JobList({ refreshKey, onOpen, search = "" }) {
  const [filter, setFilter] = useState("all");
  const [jobs, setJobs] = useState([]);
  const [err, setErr] = useState(null);

  const q = search.trim().toLowerCase();
  const visible = q
    ? jobs.filter(
        (j) =>
          j.filename.toLowerCase().includes(q) ||
          String(j.id).includes(q.replace(/^#/, ""))
      )
    : jobs;

  async function load() {
    try {
      const data = await listJobs(filter === "all" ? null : filter);
      setJobs(data);
      setErr(null);
    } catch (e) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, refreshKey]);

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 10 }}>Step 02 — Monitor</div>
      <h2>Jobs</h2>
      <p className="sub">Live status of every uploaded batch.</p>

      <div className="filters">
        {FILTERS.map((f) => (
          <span
            key={f}
            className={`chip-filter ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </span>
        ))}
      </div>

      {err && <div className="toast err">{err}</div>}
      {jobs.length === 0 && !err && <p className="muted">No jobs yet.</p>}
      {jobs.length > 0 && visible.length === 0 && (
        <p className="muted">No jobs match “{search}”.</p>
      )}

      <AnimatePresence initial={false}>
        {visible.map((j, i) => (
          <motion.div
            key={j.id}
            className="job-row"
            onClick={() => onOpen(j.id)}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: Math.min(i * 0.04, 0.3) }}
          >
            <span className={`dot-status ${j.status}`} />
            <div className="grow">
              <div className="title">
                #{j.id} · {j.filename}
              </div>
              <div className="job-meta">
                {j.row_count_clean}/{j.row_count_raw} rows · {fmt(j.created_at)}
              </div>
            </div>
            <span className={`badge ${j.status}`}>{j.status}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
