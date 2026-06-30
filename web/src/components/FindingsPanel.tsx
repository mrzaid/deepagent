import type { Finding } from "../types";

export default function FindingsPanel({ findings }: { findings: Finding[] }) {
  return (
    <div className="panel">
      <h2>Findings ({findings.length})</h2>
      {findings.length === 0 ? (
        <div className="empty">None yet.</div>
      ) : (
        findings.map((f, i) => (
          <div className="finding" key={i}>
            <div>{f.claim}</div>
            {f.quote && <div className="q">"{f.quote}"</div>}
            <div>
              <a href={f.source_url} target="_blank" rel="noreferrer">
                {f.source_url}
              </a>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
