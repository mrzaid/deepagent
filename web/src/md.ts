// Tiny, dependency-free markdown -> HTML for the report panel: headings, lists,
// bold, links, and bare URLs. Escapes first, so it is safe to inject.
function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(s: string): string {
  return s
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/(^|[\s(])(https?:\/\/[^\s)]+)/g, '$1<a href="$2" target="_blank" rel="noreferrer">$2</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

export function md(text: string): string {
  const lines = esc(text).split(/\n/);
  let html = "";
  let inList = false;
  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };
  for (const ln of lines) {
    if (/^###\s+/.test(ln)) {
      closeList();
      html += `<h3>${inline(ln.replace(/^###\s+/, ""))}</h3>`;
    } else if (/^##\s+/.test(ln)) {
      closeList();
      html += `<h2>${inline(ln.replace(/^##\s+/, ""))}</h2>`;
    } else if (/^#\s+/.test(ln)) {
      closeList();
      html += `<h1>${inline(ln.replace(/^#\s+/, ""))}</h1>`;
    } else if (/^[-*]\s+/.test(ln)) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inline(ln.replace(/^[-*]\s+/, ""))}</li>`;
    } else if (ln.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(ln)}</p>`;
    }
  }
  closeList();
  return html;
}
