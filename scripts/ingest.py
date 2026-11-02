"""Extract a source document into <project>/ref/ so the scenes can be planned from it.

usage: python ingest.py <document> <project>
Writes ref/notes.txt (all text in reading order) and, for pptx/pdf, ref/page_NN.jpg (1600px wide).
Supports .pptx .docx .pdf .ipynb .md .txt .html
"""
import json, os, re, subprocess, sys, tempfile
import common

def shape_lines(shapes):
    for sh in shapes:
        if sh.shape_type == 6:  # group
            yield from shape_lines(sh.shapes)
        elif getattr(sh, "has_table", False) and sh.has_table:
            yield "[TABLE]"
            for r in sh.table.rows:
                yield " | ".join(c.text.replace("\n", " ").strip() for c in r.cells)
            yield "[/TABLE]"
        elif getattr(sh, "has_text_frame", False) and sh.has_text_frame:
            if sh.text_frame.text.strip():
                yield sh.text_frame.text.strip()
        elif sh.shape_type == 13:  # picture
            yield "[image]"

def pptx_notes(path):
    from pptx import Presentation
    out = []
    for i, s in enumerate(Presentation(path).slides, 1):
        out += ["", f"=== Slide {i} ===", *shape_lines(s.shapes)]
        if s.has_notes_slide and s.notes_slide.notes_text_frame and s.notes_slide.notes_text_frame.text.strip():
            out.append("[NOTES] " + s.notes_slide.notes_text_frame.text.strip())
    return out

PS = r"""
$ErrorActionPreference = 'Stop'
$a = New-Object -ComObject PowerPoint.Application
$p = $a.Presentations.Open($env:M_SRC, -1, 0, 0)
$h = [int](1600 * $p.PageSetup.SlideHeight / $p.PageSetup.SlideWidth)
try { foreach ($s in $p.Slides) { $s.Export((Join-Path $env:M_OUT ('page_{0:d2}.jpg' -f $s.SlideIndex)), 'JPG', 1600, $h) } }
finally { $p.Close(); $a.Quit() }
"""

def pdf_pages(path, ref):
    import pymupdf
    doc = pymupdf.open(path)
    for i, pg in enumerate(doc, 1):
        k = 1600 / pg.rect.width
        pg.get_pixmap(matrix=pymupdf.Matrix(k, k)).save(os.path.join(ref, f"page_{i:02d}.jpg"))
    return doc

def pptx_images(path, ref):
    """PowerPoint if installed, else LibreOffice via PDF. Text-only ingest still works if both are missing."""
    if os.name == "nt":
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS], capture_output=True,
                           env={**os.environ, "M_SRC": os.path.abspath(path), "M_OUT": os.path.abspath(ref)})
        if r.returncode == 0:
            return
        print("PowerPoint export failed:", r.stderr.decode(errors="replace")[:300])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, path], check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError) as e:
            print("LibreOffice export failed:", e)
            return
        pdf_pages(os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + ".pdf"), ref).close()

def docx_notes(path):
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc, out = Document(path), []
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            p = Paragraph(el, doc)
            if p.text.strip():
                st = p.style.name if p.style is not None else "Normal"
                out.append(p.text.strip() if st == "Normal" else f"[{st}] {p.text.strip()}")
            if el.xpath(".//w:drawing"):
                out.append("[image]")
        elif el.tag.endswith("}tbl"):
            out.append("[TABLE]")
            for r in Table(el, doc).rows:
                cells = [c.text.replace("\n", " / ").strip() for c in r.cells]
                out.append(" | ".join(dict.fromkeys(cells)))  # merged cells repeat their text
            out.append("[/TABLE]")
    return out

def ipynb_notes(path):
    out = []
    for c in json.load(open(path, encoding="utf-8"))["cells"]:
        text = "".join(c.get("source", [])).strip()
        if not text:
            continue
        out += [f"[{c['cell_type'].upper()}]", text]
        for o in c.get("outputs", []):
            t = "".join(o.get("text", []) or o.get("data", {}).get("text/plain", []))
            if t.strip():
                out += ["[OUTPUT]", t.strip()[:600]]
    return out

def main(path, d):
    ref = os.path.join(d, "ref")
    os.makedirs(ref, exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pptx":
        lines = pptx_notes(path)
        pptx_images(path, ref)
    elif ext == ".docx":
        lines = docx_notes(path)
    elif ext == ".pdf":
        lines = []
        with pdf_pages(path, ref) as doc:
            for i, pg in enumerate(doc, 1):
                lines += ["", f"=== Page {i} ===", pg.get_text().strip()]
    elif ext == ".ipynb":
        lines = ipynb_notes(path)
    elif ext in (".md", ".txt", ".html", ".htm"):
        text = open(path, encoding="utf-8", errors="replace").read()
        if ext.startswith(".htm"):
            text = re.sub(r"(?is)<(script|style)\b.*?</\1>|<[^>]+>", "\n", text)
            text = re.sub(r"\n\s*\n+", "\n", text)
        lines = text.splitlines()
    else:
        raise SystemExit(f"Unsupported document type: {ext}")
    open(os.path.join(ref, "notes.txt"), "w", encoding="utf-8").write("\n".join([os.path.basename(path), ""] + lines) + "\n")
    images = sum(f.endswith(".jpg") for f in os.listdir(ref))
    print(f"ref/notes.txt: {len(lines)} lines; {images} page images in {os.path.normpath(ref)}")
    if ext == ".pptx" and not images:
        print("WARNING: no slide images. Diagrams and image-only slides are invisible; say so in the report.")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
