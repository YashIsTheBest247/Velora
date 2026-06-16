
// CSV  →  queue  →  worker  →  database, with an animated flow dot.
export default function BackendArt() {
  const ink = "#16150f";
  const soft = "#9a968b";
  return (
    <svg
      viewBox="0 0 480 260"
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMid meet"
      style={{ display: "block" }}
      role="img"
      aria-label="Backend processing pipeline"
    >
      {/* connecting flow line */}
      <path
        id="flow"
        d="M70 110 H410"
        stroke={soft}
        strokeWidth="2"
        strokeDasharray="2 8"
        strokeLinecap="round"
      >
        <animate
          attributeName="stroke-dashoffset"
          from="0"
          to="-40"
          dur="1.6s"
          repeatCount="indefinite"
        />
      </path>

      {/* travelling packet */}
      <circle r="4" fill={ink}>
        <animateMotion dur="3.2s" repeatCount="indefinite" path="M70 110 H410" />
      </circle>

      {/* 1. CSV file */}
      <g transform="translate(48 84)" fill="none" stroke={ink} strokeWidth="2.4"
         strokeLinejoin="round" strokeLinecap="round">
        <path d="M4 2 H26 L40 16 V50 a2 2 0 0 1 -2 2 H6 a2 2 0 0 1 -2 -2 Z" />
        <path d="M26 2 V16 H40" />
        <path d="M12 30 H32 M12 38 H32 M12 22 H22" stroke={soft} strokeWidth="2" />
      </g>

      {/* 2. queue */}
      <g transform="translate(150 80)" fill="none" stroke={ink} strokeWidth="2.4"
         strokeLinejoin="round" strokeLinecap="round">
        <rect x="0" y="6" width="60" height="48" rx="10" />
        <rect x="10" y="16" width="40" height="7" rx="3.5" stroke={soft} strokeWidth="2" />
        <rect x="10" y="27" width="40" height="7" rx="3.5" stroke={soft} strokeWidth="2" />
        <rect x="10" y="38" width="26" height="7" rx="3.5" />
      </g>

      {/* 3. worker (gear) */}
      <g transform="translate(270 80)" fill="none" stroke={ink} strokeWidth="2.4"
         strokeLinejoin="round" strokeLinecap="round">
        <g transform="translate(30 30)">
          <circle r="13" />
          <circle r="4.5" stroke={soft} strokeWidth="2" />
          {Array.from({ length: 8 }).map((_, i) => {
            const a = (i * Math.PI) / 4;
            const x1 = Math.cos(a) * 14;
            const y1 = Math.sin(a) * 14;
            const x2 = Math.cos(a) * 20;
            const y2 = Math.sin(a) * 20;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
          })}
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0" to="360"
            dur="6s"
            repeatCount="indefinite"
            additive="sum"
          />
        </g>
      </g>

      {/* 4. database */}
      <g transform="translate(392 80)" fill="none" stroke={ink} strokeWidth="2.4"
         strokeLinejoin="round" strokeLinecap="round">
        <ellipse cx="20" cy="10" rx="20" ry="7" />
        <path d="M0 10 V50 a20 7 0 0 0 40 0 V10" />
        <path d="M0 30 a20 7 0 0 0 40 0" stroke={soft} strokeWidth="2" />
      </g>

      {/* captions */}
      <g fill={soft} fontFamily="Quicksand, sans-serif" fontSize="13" fontWeight="600"
         textAnchor="middle">
        <text x="68" y="172">csv</text>
        <text x="180" y="172">queue</text>
        <text x="300" y="172">worker</text>
        <text x="412" y="172">store</text>
      </g>

      {/* footer line */}
      <g fill={ink} fontFamily="Quicksand, sans-serif" textAnchor="middle">
        <text x="240" y="212" fontSize="15" fontWeight="700">async pipeline</text>
        <text x="240" y="232" fontSize="12" fontWeight="500" fill={soft}>
          clean · classify · flag · summarise
        </text>
      </g>
    </svg>
  );
}
