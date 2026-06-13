# Tutorial Source

This folder contains the Dora tutorial source and supporting assets:

- `src/`: the root language landing page.
- `en/`: the English mdBook, with its own `SUMMARY.md`.
- `zh/`: the Chinese mdBook, with the same chapter order as English.
- `verification/`: runnable examples and sanitized verification records.
- `theme/`: mdBook styling and the language switcher.
- `book.toml`: root landing-page mdBook configuration.
- `build.ps1`: builds the landing page plus both language books.
- `serve.ps1`: builds everything and serves `book/` locally.

Keeping these files under one folder leaves the repository root open for other
shared assets.

Preview locally:

```powershell
./serve.ps1
```

Then open `http://localhost:3000/`.

The generated HTML includes mdBook's built-in theme selector for light and dark
reading modes, plus an `EN / 中文` switch that jumps between matching pages. The
English and Chinese sidebars are separate, so each language keeps the same
chapter order without showing the other language as a chapter group.
