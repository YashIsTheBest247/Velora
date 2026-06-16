import { useState } from "react";
import { motion } from "framer-motion";
import { DOCS_URL } from "./api";
import Logo from "./components/Logo";
import BackendArt from "./components/BackendArt";
import Upload from "./components/Upload";
import JobList from "./components/JobList";
import JobDetail from "./components/JobDetail";

const IconHome = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 11l9-8 9 8" />
    <path d="M5 10v10h5v-6h4v6h5V10" />
  </svg>
);
const IconDocs = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 4h9l5 5v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
    <path d="M13 4v6h6M8 14h8M8 17h5" />
  </svg>
);
const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4-4" />
  </svg>
);

export default function App() {
  const [openJob, setOpenJob] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [search, setSearch] = useState("");

  const openDocs = () => window.open(DOCS_URL, "_blank", "noopener");

  return (
    <div className="shell">
      <div className="frame">
        <nav className="nav">
          <div className="brand">
            <Logo />
            Velora
          </div>

          <div className="nav-icons">
            <button className="icon-btn" title="Dashboard" onClick={() => setOpenJob(null)}>
              <IconHome />
            </button>
            <button className="icon-btn" title="API Docs" onClick={openDocs}>
              <IconDocs />
            </button>
          </div>

          <div className="nav-right">
            <span className="search-pill">
              <IconSearch />
              <input
                placeholder="Search jobs…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  if (openJob !== null) setOpenJob(null);
                }}
              />
            </span>
            <span className="avatar">V</span>
          </div>
        </nav>

        {openJob === null && (
          <section className="hero">
            <div className="hero-left">
              <motion.h1
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.2, 0.7, 0.2, 1] }}
              >
                <span className="lead">transaction</span>
                processing
                <br />
                pipeline
              </motion.h1>

              <motion.div
                className="chip"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25, duration: 0.6 }}
              >
                <span className="spark">✳</span> clean · classify · flag
              </motion.div>
            </div>

            <motion.div
              className="hero-art"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.7 }}
            >
              <BackendArt />
            </motion.div>
          </section>
        )}
      </div>

      {openJob === null ? (
        <div className="container">
          <p className="section-eyebrow">Upload &amp; monitor</p>
          <div className="grid-2">
            <motion.div
              initial={{ opacity: 0, y: 22 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
            >
              <Upload
                onUploaded={(id) => {
                  setRefreshKey((k) => k + 1);
                  setOpenJob(id);
                }}
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 22 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
            >
              <JobList refreshKey={refreshKey} onOpen={setOpenJob} search={search} />
            </motion.div>
          </div>
        </div>
      ) : (
        <div className="container">
          <JobDetail jobId={openJob} onBack={() => setOpenJob(null)} />
        </div>
      )}
    </div>
  );
}
