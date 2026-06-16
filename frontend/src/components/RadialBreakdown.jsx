import { motion } from "framer-motion";

// Clean editorial horizontal bars — label, animated fill, bold pink percentage.
export default function RadialBreakdown({ breakdown }) {
  const entries = Object.entries(breakdown || {}).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
  const max = entries.length ? entries[0][1] : 1;

  return (
    <div className="bars">
      {entries.map(([cat, val], i) => {
        const pct = Math.round((val / total) * 100);
        const width = `${Math.max((val / max) * 100, 3)}%`;
        return (
          <motion.div
            className="bar-row"
            key={cat}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06, duration: 0.4, ease: "easeOut" }}
          >
            <div className="bar-label">{cat}</div>
            <div className="bar-track">
              <motion.div
                className={`bar-fill ${i === 0 ? "lead" : ""}`}
                initial={{ width: 0 }}
                animate={{ width }}
                transition={{ delay: 0.15 + i * 0.06, duration: 0.8, ease: "easeOut" }}
              />
            </div>
            <div className="bar-pct">{pct}%</div>
          </motion.div>
        );
      })}
    </div>
  );
}
