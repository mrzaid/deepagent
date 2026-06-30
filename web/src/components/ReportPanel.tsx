import { md } from "../md";

export default function ReportPanel({ report, streaming }: { report: string; streaming: boolean }) {
  if (!report && !streaming) return null;
  const html = md(report) + (streaming ? '<span class="caret">▌</span>' : "");
  return (
    <>
      <div className="panel" style={{ marginBottom: 6 }}>
        <h2>Final report</h2>
      </div>
      <div className="report" dangerouslySetInnerHTML={{ __html: html }} />
    </>
  );
}
