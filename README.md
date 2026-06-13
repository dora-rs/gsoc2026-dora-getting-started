# GSoC 2026 Dora Getting Started

This repository collects the weekly deliverables for the GSoC 2026 project
"Enhance and restructure DORA getting started guides, tutorials, and onboarding
documentation for new developers and contributors."

The work product is organized as a readable book plus one video asset area per
week. Verification code and scripts live beside the book so future weeks can
repeat the same "write, run, document" loop.

## Current Status

- Active work branch: `week1-docs-assets`
- Student work product root: [`work-product`](work-product)
- Book entry point: [`work-product/src/index.md`](work-product/src/index.md)
- Week 1 English documentation: [`work-product/en/src/weeks/week-01-dora-introduction-installation-hello-world.md`](work-product/en/src/weeks/week-01-dora-introduction-installation-hello-world.md)
- Week 1 Chinese documentation: [`work-product/zh/src/weeks/week-01-dora-introduction-installation-hello-world.md`](work-product/zh/src/weeks/week-01-dora-introduction-installation-hello-world.md)
- Week 1 verification: [`work-product/verification/week1-hello-world`](work-product/verification/week1-hello-world)
- Video assets: [`work-product/videos`](work-product/videos)
- Proposal source: [`gsoc_2026_improve_getting_started_documentation_qiyang_tan_revised.pdf`](gsoc_2026_improve_getting_started_documentation_qiyang_tan_revised.pdf)

## Repository Layout

```text
.
|-- CLAUDE.md
|-- README.md
|-- gsoc_2026_improve_getting_started_documentation_qiyang_tan_revised.pdf
`-- work-product/
    |-- book.toml
    |-- build.ps1
    |-- serve.ps1
    |-- en/
    |   |-- book.toml
    |   `-- src/
    |-- zh/
    |   |-- book.toml
    |   `-- src/
    |-- src/
    |   |-- SUMMARY.md
    |   `-- index.md
    |-- videos/
    |   |-- README.md
    |   `-- week-01 ... week-13/
    |-- verification/
    |   |-- README.md
    |   `-- week1-hello-world/
    `-- theme/
        `-- dora.css
```

## Reading the Book

The book is plain Markdown and can be read directly in GitHub. If `mdbook` is
installed locally, preview it with:

```powershell
cd work-product
./serve.ps1
```

The custom CSS in `work-product/theme/dora.css` keeps the rendered book
restrained, clean, and comfortable for long reading sessions. `serve.ps1` builds
the root landing page plus the English and Chinese books, then serves the
combined `work-product/book/` output.

## Verification

Week 1 includes a minimal dora-rs Python dataflow:

```powershell
cd work-product/verification/week1-hello-world
./run.ps1
```

The script creates an isolated `.venv`, installs pinned dora-rs packages, runs
the dataflow, and fails if the listener output is missing.

## Privacy

Do not copy private contact details, tokens, local usernames, or machine-specific
paths into public documentation. Committed verification notes use placeholder
paths such as `<repo>` and `<temp>`.
