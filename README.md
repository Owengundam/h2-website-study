# H2 Architecture — website study archive

Public frontend captured from https://www.h2arch.com/ on 2026-10-08, starting with https://www.h2arch.com/projects/ and following English and Chinese pages and their dependencies.

**Partial capture:** 52 unique public pages and 629 successful resource URLs were retained. Later downloads were rejected by the environment's network proxy (CONNECT 403), leaving some media, fonts, and styles unavailable locally. Those references retain their live source URLs. Two truncated images were removed. The English homepage also returned a redirect loop. See `STUDY.md` and `validation.json` before relying on offline completeness.

## Open the copy

Requires Python 3. From this directory:

```sh
python3 serve.py
```

On Windows, use `py serve.py`. Open http://localhost:8000/ . Keep the terminal running. Use a local HTTP server rather than double-clicking individual HTML files; the archive uses root-relative asset links.

## Contents

- `site/`: captured HTML, CSS, JavaScript, images, and fonts, grouped by source host.
- `capture-manifest.json`: source URL, local path, file size, and capture status.
- `STUDY.md`: capture coverage and known limitations.
- `scripts/mirror.py`: reproducible public-site crawler (Python standard library and curl).
- `serve.py`: local preview server, bound to localhost.

This is a static frontend archive, not the original WordPress source repository or database. Server-side search, contact-form submission, and WordPress AJAX functions need the original backend. Links to third-party services remain external. The manifest records unsuccessful downloads explicitly.

Original H2 branding, project photographs, text, and third-party theme/plugin assets retain their respective owners' rights. No license to redistribute those materials is implied. This archive is intended for a private website study.

## Create a private GitHub repository

If the repository has not already been created, install and sign into GitHub CLI, then run from this directory:

```sh
git init -b main
git add .
git commit -m "Archive H2 public website for private study"
gh repo create h2-website-study --private --source=. --remote=origin --push
```

If an individual archived asset exceeds GitHub's normal file-size limit, track it with Git LFS before committing. Capture size and large-file checks are recorded in `STUDY.md`.
