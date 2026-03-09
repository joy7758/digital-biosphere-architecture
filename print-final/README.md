# Print Final

This folder is the print production handoff package.

Rules:
- print vendors receive PDF exports only
- Markdown files remain the source of truth for wording and QR targets

Build source:
- `design-src/build_print_assets.py`
- `design-src/qr_tools.swift`

Source of truth:
- `source-of-truth/poster-sync.md`
- `source-of-truth/print-copy.md`
- `poster/qr-links-source.md`

Generated files:
- `poster/A1-poster-final.pdf`
- `card/one-pager-front-back.pdf`
- `card/business-card-final.pdf`
- `card/business-card-10up-A4.pdf`

QR assets:
- `poster/qr/`
- `card/qr/`
- `business-card/qr/`

Build command:
- `python3 print-final/design-src/build_print_assets.py`
