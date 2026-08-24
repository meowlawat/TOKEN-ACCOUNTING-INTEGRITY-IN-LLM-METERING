# Author photograph — supplied

**Status: READY.** `paper/submission_forms/author_photo.jpg`

```
1200 x 1600 px, 300 dpi  (4.00 x 5.33 inches at print size)
JPEG, quality 95, no chroma subsampling
white background, head-and-shoulders portrait
0.54 MB
```

Elsevier's *Computers & Security* author guide requests a short biography and a
passport-style photograph per author. This closes the photograph half;
`paper/author_bio.txt` holds the biography, which still needs the author's review.

## Requirements, and how this file meets them

| requirement | status |
|---|---|
| Subject alone, facing the camera | yes |
| Passport / headshot framing | yes — cropped to 3:4 head-and-shoulders |
| Plain uncluttered background | yes — plain white |
| JPEG or TIFF | JPEG |
| 300 dpi minimum at printed size | 300 dpi, stamped in the file |
| Colour | colour |

Verify these against the live author guide at submission time rather than trusting this
table — Elsevier's requirements change.

## How it was prepared

`scripts/prepare_author_photo.py`, from the source the author supplied. Framing and
format only: flatten the transparent background onto white (JPEG carries no alpha), crop
to a 3:4 portrait with conventional headroom above the crown, resize to 1200x1600, stamp
300 dpi, write JPEG at quality 95.

No retouching. Nothing about the subject was altered.

## Provenance

The source file came from Google's Gemini. The author confirms it is a real photograph of
them with the background edited — the same thing a photo studio does to produce a passport
shot — not a synthetic likeness.

That distinction was checked before this file was prepared, and it is the only reason this
file exists: an AI-generated portrait presented as a real person's author photograph would
be a fabricated record, and would not have been packaged regardless of how the request was
framed.

The head-and-shoulders crop excludes the lower corners of the source frame, where Gemini's
visible marker sat. That is a consequence of correct passport framing, not the goal. Any
invisible SynthID watermark in the remaining pixels is untouched — provenance marking is
not something to strip, and there is no reason to here.

## Where it goes

Uploaded through Editorial Manager as a separate item, not embedded in `main_cose.tex`.
The manuscript compiles and is complete without it; this is a submission-system field, not
a LaTeX dependency.

## Related

- `paper/author_bio.txt` — the accompanying biography. Requested together, so supply them
  together. Still needs the author's review.
- `paper/FINAL_SUBMISSION_MANIFEST.md` — full packing list.
