import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getResults, getStatus } from "../api";
import CountUp from "./CountUp";
import RadialBreakdown from "./RadialBreakdown";

function Row({ t }) {
  return (
    <tr className={t.is_anomaly ? "anomaly" : ""}>
      <td>{t.txn_id || "—"}</td>
      <td>{t.date || "—"}</td>
      <td>{t.merchant || "—"}</td>
      <td className="num">
        {t.amount == null ? "—" : Number(t.amount).toLocaleString()}
      </td>
      <td>{t.currency || "—"}</td>
      <td>{t.status || "—"}</td>
      <td>
        {t.category}
        {t.llm_category && (
          <span className="muted"> {t.llm_failed ? "(llm⚠)" : "(ai)"}</span>
        )}
      </td>
      <td>{t.account_id || "—"}</td>
      <td>{t.is_anomaly ? "⚠️" : ""}</td>
    </tr>
  );
}

const StatCard = ({ k, children, delay }) => (
  <motion.div
    className="stat"
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5 }}
  >
    <div className="k">{k}</div>
    <div className="v">{children}</div>
  </motion.div>
);

export default function JobDetail({ jobId, onBack }) {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let active = true;
    async function tick() {
      try {
        const s = await getStatus(jobId);
        if (!active) return;
        setStatus(s);
        if (s.status === "completed" && !results) {
          const r = await getResults(jobId);
          if (active) setResults(r);
        }
      } catch (e) {
        if (active) setErr(e.message);
      }
    }
    tick();
    const t = setInterval(tick, 2000);
    return () => {
      active = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const s = status;
  const summary = results?.summary || s?.summary;

  return (
    <div style={{ paddingTop: 8 }}>
      <span className="back" onClick={onBack}>
        ← Back to dashboard
      </span>

      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span className={`dot-status ${s?.status || "pending"}`} />
            <div>
              <h2 style={{ margin: 0 }}>
                Job #{jobId} {s ? `· ${s.filename}` : ""}
              </h2>
              <p className="sub" style={{ margin: "4px 0 0" }}>
                {s ? `${s.row_count_clean}/${s.row_count_raw} clean rows` : "Loading…"}
              </p>
            </div>
          </div>
          {s && <span className={`badge ${s.status}`}>{s.status}</span>}
        </div>

        {err && <div className="toast err" style={{ marginTop: 16 }}>{err}</div>}
        {s?.error_message && (
          <div className="toast err" style={{ marginTop: 16 }}>{s.error_message}</div>
        )}

        {s && s.status !== "completed" && s.status !== "failed" && (
          <div className="processing-pulse">
            <span className="dot-status processing" />
            Processing — this view updates automatically…
          </div>
        )}
      </div>

      {summary && (
        <>
          <div className="stats">
            <StatCard k="Total spend (INR)" delay={0.05}>
              <CountUp value={summary.total_spend_inr} decimals={0} prefix="₹" />
            </StatCard>
            <StatCard k="Total spend (USD)" delay={0.12}>
              <CountUp value={summary.total_spend_usd} decimals={0} prefix="$" />
            </StatCard>
            <StatCard k="Anomalies" delay={0.19}>
              <CountUp value={summary.anomaly_count} />
            </StatCard>
            <StatCard k="Risk level" delay={0.26}>
              <span className={`badge ${summary.risk_level}`}>
                {summary.risk_level}
              </span>
            </StatCard>
          </div>

          <motion.div
            className="card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32, duration: 0.5 }}
          >
            <h2>Narrative summary</h2>
            <p className="sub">LLM-generated overview of this batch.</p>
            <div className="narrative">{summary.narrative}</div>

            <div className="section-title">Top merchants</div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Merchant</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {(summary.top_merchants || []).map((m) => (
                    <tr key={m.merchant}>
                      <td>{m.merchant}</td>
                      <td className="num">{Number(m.total).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="section-title">Spend by category</div>
            <RadialBreakdown
              breakdown={results?.category_breakdown || summary.category_breakdown}
            />
          </motion.div>
        </>
      )}

      {results && results.anomalies.length > 0 && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h2>Flagged anomalies ({results.anomalies.length})</h2>
          <p className="sub">Statistical outliers and currency mismatches.</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Txn</th>
                  <th>Merchant</th>
                  <th>Amount</th>
                  <th>Cur</th>
                  <th>Account</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {results.anomalies.map((t) => (
                  <tr key={t.id} className="anomaly">
                    <td>{t.txn_id || "—"}</td>
                    <td>{t.merchant}</td>
                    <td className="num">{Number(t.amount).toLocaleString()}</td>
                    <td>{t.currency}</td>
                    <td>{t.account_id}</td>
                    <td style={{ whiteSpace: "normal" }}>{t.anomaly_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {results && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h2>Cleaned transactions ({results.transactions.length})</h2>
          <p className="sub">Normalised dates, amounts, status and categories.</p>
          <div className="table-wrap" style={{ maxHeight: 460 }}>
            <table>
              <thead>
                <tr>
                  <th>Txn</th>
                  <th>Date</th>
                  <th>Merchant</th>
                  <th>Amount</th>
                  <th>Cur</th>
                  <th>Status</th>
                  <th>Category</th>
                  <th>Account</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {results.transactions.map((t) => (
                  <Row key={t.id} t={t} />
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </div>
  );
}
