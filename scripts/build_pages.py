#!/usr/bin/env python3
"""Prepare the captured archive for a GitHub Pages project subdirectory."""
import os
import re
import shutil
from pathlib import Path

source = Path("site")
target = Path("_site")
base = "/" + os.environ.get("GITHUB_REPOSITORY", "Owengundam/h2-website-study").split("/")[-1]
shutil.copytree(source, target, dirs_exist_ok=True)
hosts = [p.name for p in source.iterdir() if p.is_dir()]
pattern = re.compile(r'(?<![A-Za-z0-9_/:.-])/(?:' + "|".join(re.escape(h) for h in hosts) + r')/')
count = 0
for path in target.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".json", ".svg"}:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = re.sub(r"https:/(?!/)", "https://", text)
        text = re.sub(r"http:/(?!/)", "http://", text)
        text = pattern.sub(lambda m: base + m.group(0), text)
        path.write_text(text, encoding="utf-8")
        count += 1
(target / ".nojekyll").touch()
assert (target / "index.html").is_file()
assert (target / "www.h2arch.com/projects/index.html").is_file()
print(f"Prepared {count} text files for {base}/")
