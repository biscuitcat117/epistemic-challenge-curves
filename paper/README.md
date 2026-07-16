# Paper source

This folder contains the manuscript source and compiled PDF.

- `main.tex` is the LaTeX manuscript source. The figure is drawn directly in
  this file, so no separate image files are required.
- `references.bib` contains the bibliography.
- `draft-paper.pdf` is the compiled 15-page draft.

## Build locally

With a standard TeX Live installation:

```bash
latexmk -pdf main.tex
```

On Overleaf, upload `main.tex` and `references.bib`, then compile `main.tex`
with pdfLaTeX. Generated files such as `.aux`, `.bbl`, `.blg`, `.log`, and
`.out` are build by-products and are not kept in the repository.
