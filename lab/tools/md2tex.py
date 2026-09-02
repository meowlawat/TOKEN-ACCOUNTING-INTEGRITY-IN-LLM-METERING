"""Convert lab/SE_LAB_FILE.md to LaTeX, substituting rendered mermaid PNGs.

Targeted at the structure this specific document uses: ATX headings, pipe tables,
fenced code blocks, mermaid blocks, bullet/numbered lists, bold/italic/inline code,
links and horizontal rules. Not a general Markdown implementation.
"""
import re
import pathlib

SRC = pathlib.Path("lab/SE_LAB_FILE.md")
OUT = pathlib.Path("lab/tools/lab_file.tex")
DIAG = "diagrams"

# ---------------------------------------------------------------- inline handling
SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def esc(s: str) -> str:
    out = []
    for ch in s:
        out.append(SPECIALS.get(ch, ch))
    return "".join(out)


def inline(s: str) -> str:
    """Handle `code`, **bold**, *italic*, [text](url) with correct escaping."""
    parts = []
    # protect inline code first
    for i, seg in enumerate(re.split(r"(`[^`]+`)", s)):
        if i % 2 == 1:
            parts.append(r"\texttt{" + esc(seg[1:-1]) + "}")
            continue
        # links -> just the text, url in footnote-free form
        seg = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", seg)
        # split on bold, then italic
        buf = []
        for j, b in enumerate(re.split(r"(\*\*[^*]+\*\*)", seg)):
            if j % 2 == 1:
                buf.append(r"\textbf{" + esc(b[2:-2]) + "}")
            else:
                sub = []
                for k, it in enumerate(re.split(r"\*([^*]+)\*", b)):
                    sub.append(r"\emph{" + esc(it) + "}" if k % 2 == 1 else esc(it))
                buf.append("".join(sub))
        parts.append("".join(buf))
    out = "".join(parts)
    out = out.replace("---", "---").replace("→", r"$\rightarrow$")
    out = out.replace("≤", r"$\leq$").replace("≥", r"$\geq$")
    out = out.replace("×", r"$\times$").replace("Σ", r"$\Sigma$")
    out = out.replace("✅", r"[Y]").replace("⚠️", r"[!]").replace("⚠", r"[!]")
    out = out.replace("’", "'").replace("‘", "'")
    out = out.replace("“", "``").replace("”", "''")
    out = out.replace("–", "--").replace("—", "---")
    out = out.replace("μ", r"$\mu$").replace("≈", r"$\approx$")
    return out


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").split("\n")
    body: list[str] = []
    i = 0
    diagram_no = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        ln = lines[i]

        # ---- fenced blocks ----------------------------------------------------
        m = re.match(r"^```(\w*)", ln)
        if m and not in_code:
            lang = m.group(1)
            if lang == "mermaid":
                diagram_no += 1
                # skip to closing fence
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    i += 1
                png = f"{DIAG}/diagram_{diagram_no:02d}.png"
                body.append(r"\begin{center}")
                body.append(
                    r"\includegraphics[width=\linewidth,height=0.78\textheight,"
                    r"keepaspectratio]{" + png + "}")
                body.append(r"\end{center}")
                i += 1
                continue
            in_code = True
            code_buf = []
            i += 1
            continue
        if ln.startswith("```") and in_code:
            in_code = False
            body.append(r"\begin{lstlisting}")
            body.extend(code_buf)
            body.append(r"\end{lstlisting}")
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue

        # ---- tables -----------------------------------------------------------
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            n = len(header)
            widths = {2: ["0.30", "0.62"], 3: ["0.16", "0.30", "0.46"],
                      4: ["0.10", "0.28", "0.20", "0.34"],
                      5: ["0.08", "0.24", "0.18", "0.18", "0.24"],
                      6: ["0.08", "0.20", "0.16", "0.16", "0.16", "0.16"]}
            spec = widths.get(n, ["%.2f" % (0.92 / n)] * n)
            colspec = "".join(">{\\raggedright\\arraybackslash}p{%s\\textwidth}" % w for w in spec)
            body.append(r"\begin{center}\small")
            body.append(r"\begin{longtable}{" + colspec + "}")
            body.append(r"\toprule")
            body.append(" & ".join(r"\textbf{" + inline(h) + "}" for h in header) + r" \\")
            body.append(r"\midrule\endhead")
            for r in rows:
                r = (r + [""] * n)[:n]
                body.append(" & ".join(inline(c) for c in r) + r" \\")
            body.append(r"\bottomrule")
            body.append(r"\end{longtable}")
            body.append(r"\end{center}")
            continue

        # ---- headings ---------------------------------------------------------
        if ln.startswith("# "):
            body.append(r"\clearpage")
            body.append(r"\section*{" + inline(ln[2:]) + "}")
            body.append(r"\addcontentsline{toc}{section}{" + inline(ln[2:]) + "}")
            i += 1
            continue
        if ln.startswith("## "):
            body.append(r"\subsection*{" + inline(ln[3:]) + "}")
            i += 1
            continue
        if ln.startswith("### "):
            body.append(r"\subsubsection*{" + inline(ln[4:]) + "}")
            i += 1
            continue

        # ---- horizontal rule --------------------------------------------------
        if re.match(r"^---+$", ln.strip()):
            i += 1
            continue

        # ---- lists ------------------------------------------------------------
        if re.match(r"^\s*[-*] ", ln):
            items = []
            while i < len(lines):
                if re.match(r"^\s*[-*] ", lines[i]):
                    items.append(re.sub(r"^\s*[-*] ", "", lines[i]))
                    i += 1
                # an indented, non-bullet line continues the previous item
                elif items and re.match(r"^\s+\S", lines[i]):
                    items[-1] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            body.append(r"\begin{itemize}[leftmargin=1.4em,itemsep=1pt,topsep=3pt]")
            body.extend(r"\item " + inline(x) for x in items)
            body.append(r"\end{itemize}")
            continue
        if re.match(r"^\s*\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\. ", lines[i]):
                items.append(re.sub(r"^\s*\d+\. ", "", lines[i]))
                i += 1
            body.append(r"\begin{enumerate}[leftmargin=1.6em,itemsep=1pt,topsep=3pt]")
            body.extend(r"\item " + inline(x) for x in items)
            body.append(r"\end{enumerate}")
            continue

        # ---- blank / paragraph ------------------------------------------------
        if not ln.strip():
            body.append("")
        else:
            body.append(inline(ln))
        i += 1

    tex = PREAMBLE + "\n".join(body) + "\n\\end{document}\n"
    OUT.write_text(tex, encoding="utf-8", newline=chr(10))
    print(f"wrote {OUT}  ({len(tex):,} chars, {diagram_no} diagrams referenced)")


PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[a4paper,left=2.2cm,right=2.2cm,top=1.2cm,bottom=2.2cm,%
            headheight=152pt,headsep=16pt,footskip=26pt,includehead]{geometry}
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{parskip}

\lstset{
  basicstyle=\ttfamily\footnotesize,
  breaklines=true,
  frame=single,
  rulecolor=\color{gray!50},
  backgroundcolor=\color{gray!6},
  columns=fullflexible,
  keepspaces=true,
  literate={→}{{$\rightarrow$}}1 {≤}{{$\leq$}}1 {≥}{{$\geq$}}1 {×}{{$\times$}}1
           {≈}{{$\approx$}}1 {μ}{{$\mu$}}1 {Σ}{{$\Sigma$}}1 {–}{{-}}1 {—}{{---}}1
}

% ---------------------------------------------------------------------------
% Header / footer reproduced from the VIPS-TC Software Engineering Lab Manual.
% Colours, point sizes, wording and the logo are taken from the manual itself
% (red #FF0000, cyan #00B0F0, Calibri 10.1pt header, 12pt footer) so the page
% furniture matches the source document exactly.
% ---------------------------------------------------------------------------
\usepackage{fontspec}
\newfontfamily\calibri{Calibri}[
  BoldFont       = Calibri Bold,
  ItalicFont     = Calibri Italic,
  BoldItalicFont = Calibri Bold Italic]

\definecolor{vipsred}{HTML}{FF0000}
\definecolor{vipsblue}{HTML}{00B0F0}

\newcommand{\vipsheader}{%
  \begin{minipage}{\textwidth}
  \centering
  \includegraphics[height=62.7pt]{assets/vips_logo.png}\\[1pt]
  {\calibri\bfseries\color{vipsred}\fontsize{10.1}{12.2}\selectfont
    VIVEKANANDA INSTITUTE OF PROFESSIONAL STUDIES - TECHNICAL CAMPUS\par}
  {\calibri\bfseries\fontsize{10.1}{12.2}\selectfont
    Grade \textcolor{vipsred}{A++} Accredited Institution by NAAC\par}
  {\calibri\fontsize{10.1}{12.2}\selectfont
    NBA Accredited for MCA Programme; Recognized under Section 2(f) by UGC;\par}
  {\calibri\fontsize{10.1}{12.2}\selectfont
    Affiliated to GGSIP University, Delhi; Recognized by Bar Council of India and AICTE\par}
  {\calibri\fontsize{10.1}{12.2}\selectfont
    An ISO 9001:2015 Certified Institution\par}
  {\calibri\color{vipsblue}\fontsize{10.1}{12.2}\selectfont
    SCHOOL OF ENGINEERING \& TECHNOLOGY\par}
  \end{minipage}}

\newcommand{\vipsfooter}{%
  {\fontsize{12}{14}\selectfont
   VIPS -TC , Software Engineering Lab Manual , 5\textsuperscript{th} Sem}}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\vipsheader}
\fancyfoot[L]{\fontsize{12}{14}\selectfont\thepage}
\fancyfoot[C]{\vipsfooter}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\setlength{\headheight}{152pt}
\setlength{\headsep}{16pt}

% The title page carries the same furniture as every other page.
\fancypagestyle{plain}{%
  \fancyhf{}
  \fancyhead[C]{\vipsheader}
  \fancyfoot[L]{\fontsize{12}{14}\selectfont\thepage}
  \fancyfoot[C]{\vipsfooter}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}}

\setlength{\emergencystretch}{3em}
\sloppy

\begin{document}

\thispagestyle{plain}
\begingroup
\centering
\vspace*{0.3cm}
\vspace{0.4cm}
{\normalsize Department of Computer Science \& Engineering\par}
\vspace{1.6cm}
{\Huge\bfseries Software Engineering\par}
\vspace{0.3cm}
{\Huge\bfseries Practical File\par}
\vspace{0.6cm}
{\large Course Code: CIC-357 \quad|\quad 5th Semester\par}
\vspace{1.8cm}
\rule{0.8\textwidth}{0.4pt}\\[0.5cm]
{\large\bfseries Project\par}
\vspace{0.3cm}
{\large Token-Accounting Integrity in LLM Metering:\\[3pt]
A Systematic Study of Client-Side Under-Payment\par}
\vspace{0.4cm}
\rule{0.8\textwidth}{0.4pt}
\vspace{1.8cm}

{\large Submitted by: \textbf{Hardik}\par}
\vspace{2.5cm}
{\small Experiments 1--13 \quad|\quad All artefacts derived from the existing project repository\par}
\vfill
\par
\endgroup
\clearpage

\tableofcontents
\clearpage

"""

if __name__ == "__main__":
    main()
