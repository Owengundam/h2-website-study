# H2 Architecture — editorial redesign

Isolated design-study branch: `redesign/k-studio-indigo`. This does not replace the official h2arch.com website or modify the captured archive on `main`.

## Run locally

From the repository root:

```sh
python -m pip install beautifulsoup4 Pillow
python scripts/build_redesign.py
python -m http.server 8000
```

Open `http://localhost:8000/redesign/`. The checked-in generated pages also work without rebuilding. Content and navigation are actual HTML; JavaScript only enhances filtering, image viewing and sharing.

## Scope

40 pages: English and Chinese Work, 13 project pages, Studio, Journal, two full articles and Contact. The Work page reimplements the reference's five-column, edge-to-edge portrait image wall. K-Studio was a visual reference only: no K-Studio photographs, source code, branding or font files are included.

Nalati Indigo is the developed case study, with Challenge / Solution / Outcome / Film / Details. It uses H2's existing photography and three distinct, timestamped frames from the 15.32-second project film. The film is design-stage visualization, not a completion survey. The local MP4 is a compressed silent web edit.

The source archive contains truncated JPEGs. Strict decoding rejects them, rather than showing partially decoded gray blocks. See `build-report.json` and `assets/source-manifest.json` for the exact exclusions and image provenance. The Hyatt Shijiazhuang gallery in the captured source mixes unrelated Resea photographs; these are not republished in that project's redesign.

## Editing

- `scripts/build_redesign.py`: page templates, bilingual copy, curated projects and source records.
- `redesign/site.css`: base editorial design system.
- `redesign/reference-layout.css`: image-wall/reference treatment and responsive overrides.
- `redesign/site.js`: progressive-enhancement controls.
- `scripts/test_redesign.py`: static links, browser behavior, responsive layouts, video and no-JavaScript tests.
- `redesign/assets/source-manifest.json`: output images, original paths and film timestamps.

The compressed source bundle under `redesign/bootstrap/` is a one-time transport record used by the connector-driven bootstrap. The bootstrap removes it after decoding and commits the ordinary editable files. Subsequent builds use those files directly.

## Preview vs. official launch

The study is `noindex,follow` by default to avoid competing with the official site. No analytics, remote font requests, newsletter backend or simulated form submission are included. Project contact actions use the existing email and telephone details.

Before an official launch, H2 should approve the editorial synthesis, confirm current project names and status, verify contractual roles/collaborators, and complete photography/video permissions and credits. The case study is not presented as a founder quotation. Interior imagery does not imply H2's interior-design authorship. No occupancy, revenue, environmental-performance or post-occupancy results are invented.

After editorial approval, build with `H2_PRODUCTION_URL=https://the-approved-domain.example` to switch canonical URLs and opt into indexing. Do not use a guessed official domain.

## Tests

```sh
python -m pip install playwright
python -m playwright install --with-deps chromium
python scripts/test_redesign.py
```

Tests write desktop/mobile captures and a detailed JSON report under `redesign-qa/`.
