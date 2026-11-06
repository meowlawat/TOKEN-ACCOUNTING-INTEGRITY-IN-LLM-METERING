# Clean TAISAP PDF inspection

- Named build: 32 pages; 85 rendered numbered references; log findings: none.
- Anonymous build: 32 pages; 85 rendered numbered references; log findings: none.
- Bibliography: 85 entries, 85 cited keys, 85 clean-build BBL entries.
- Reference-verification class: all 85 are inherited/unchecked in this upgrade; prior verification reports are inputs, not independent evidence for this checkpoint.
- Missing cited keys: none; cited keys absent from clean BBL: none.
- Anonymous source identity/artifact findings: ['hardik', 'natasha', 'iit_patna', 'vips', 'author_email', 'zenodo'].
- Anonymous rendered-text findings: ['zenodo'].
- Anonymous PDF metadata findings: none.
- Existing named PDF matches clean build: False; existing anonymous PDF matches clean build: False (creation timestamps make byte equality non-semantic, so page/text findings govern).

The anonymous source retains author metadata inside `\author` commands; the class may suppress it visually, but source submission would disclose it. Public Zenodo DOIs also remain in rendered text and are author-linked. Both are anonymity defects, not clean-build failures.

## Visual inspection

Rendered PNGs were inspected at 120 dpi for named pages 1, 14, and 32 and anonymous
pages 1 and 32. The title blocks, body text, running heads, equations, and final reference
page were legible, inside page bounds, and free of visible overlap or clipping. The
anonymous title page rendered `ANONYMOUS AUTHOR(S)` and its running head rendered `Anon.`;
the source-level identities described above remain a source-package defect. The rendered
anonymous Zenodo identifiers occur in the data-availability section and remain a
double-anonymity defect even though the sampled first and last pages are visually clean.
