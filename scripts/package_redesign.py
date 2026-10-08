#!/usr/bin/env python3
"""Publish the committed redesign at the existing GitHub Pages project root.

The captured archive stays in git. Preview noindex settings remain unchanged.
This packager needs only the Python standard library and performs no network I/O.
"""
from __future__ import annotations
import ast
import html
import json
import os
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "redesign"
TARGET = ROOT / "_site"
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "Owengundam/h2-website-study")
OWNER, NAME = REPOSITORY.split("/", 1)
BASE = f"https://{OWNER.lower()}.github.io/{NAME}"
OLD_BASE = "https://owengundam.github.io/h2-website-study/redesign"


def redirect(relative: Path | str, destination: str) -> None:
    file = TARGET / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    url = BASE + "/" + destination.lstrip("/")
    escaped = html.escape(url, quote=True)
    file.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,follow"><title>H2 Architecture</title>'
        f'<link rel="canonical" href="{escaped}">'
        f'<meta http-equiv="refresh" content="0;url={escaped}">'
        f'<script>location.replace({json.dumps(url)}+location.search+location.hash);</script>'
        f'</head><body><a href="{escaped}">Continue to H2 Architecture</a></body></html>',
        encoding="utf-8",
    )


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if not value:
                continue
            if key in {"href", "src", "poster"}:
                self.urls.append(value)
            elif key == "srcset":
                self.urls.extend(item.strip().split()[0] for item in value.split(",") if item.strip())


def main() -> None:
    required = ["index.html", "projects/nalati-indigo/index.html", "cn/index.html", "site.css", "site.js"]
    for relative in required:
        if not (SOURCE / relative).is_file():
            raise RuntimeError(f"Missing redesign file: {relative}")
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(SOURCE, TARGET)
    for file in TARGET.rglob("*"):
        if file.is_file() and file.suffix.lower() in {".html", ".xml", ".json", ".txt"}:
            text = file.read_text(encoding="utf-8")
            file.write_text(text.replace(OLD_BASE, BASE), encoding="utf-8")
    pages = sorted(TARGET.rglob("*.html"))
    # Keep previously shared /redesign/ addresses pointing to the new root.
    for file in pages:
        relative = file.relative_to(TARGET)
        redirect(Path("redesign") / relative, relative.as_posix())
    # Preserve commonly shared addresses from the original captured website.
    aliases = {
        "www.h2arch.com/index.html": "index.html",
        "www.h2arch.com/projects/index.html": "work/index.html",
        "www.h2arch.com/profile/index.html": "studio/index.html",
        "www.h2arch.com/contact/index.html": "contact/index.html",
        "www.h2arch.com/cn/home-cn/index.html": "cn/index.html",
        "www.h2arch.com/cn/projects-cn/index.html": "cn/work/index.html",
    }
    # Read only the literal project mapping; do not execute the site builder.
    tree = ast.parse((ROOT / "scripts/build_redesign.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in node.targets):
            for source_slug, slug, *_ in ast.literal_eval(node.value):
                aliases[f"www.h2arch.com/portfolio-item/{source_slug}/index.html"] = f"projects/{slug}/index.html"
    for old, new in aliases.items():
        if not (TARGET / new).is_file():
            raise RuntimeError(f"Missing redirect destination: {new}")
        redirect(old, new)
    (TARGET / ".nojekyll").touch()
    (TARGET / "deployment.json").write_text(json.dumps({
        "site": "H2 editorial redesign", "base_url": BASE + "/",
        "commit": os.environ.get("GITHUB_SHA", "local"), "pages": len(pages),
    }, indent=2), encoding="utf-8")

    checked = 0
    for file in TARGET.rglob("*.html"):
        parser = Links()
        parser.feed(file.read_text(encoding="utf-8"))
        page_url = BASE + "/" + file.relative_to(TARGET).as_posix()
        for value in parser.urls:
            url = urlsplit(urljoin(page_url, value))
            if url.scheme not in {"http", "https"} or url.netloc != urlsplit(BASE).netloc:
                continue
            prefix = urlsplit(BASE).path + "/"
            if not url.path.startswith(prefix):
                raise RuntimeError(f"Link escapes Pages project: {file}: {value}")
            target = TARGET / unquote(url.path[len(prefix):])
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                raise RuntimeError(f"Broken published link: {file}: {value}")
            checked += 1
    print(f"Prepared {len(pages)} redesign pages at {BASE}/; verified {checked} local links and media references.")


if __name__ == "__main__":
    main()
