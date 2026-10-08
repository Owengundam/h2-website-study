#!/usr/bin/env python3
"""Prepare the captured archive for a GitHub Pages project subdirectory."""
import os
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

source = Path("site")
target = Path("_site")
base = "/" + os.environ.get("GITHUB_REPOSITORY", "Owengundam/h2-website-study").split("/")[-1]
shutil.copytree(source, target, dirs_exist_ok=True)
hosts = [p.name for p in source.iterdir() if p.is_dir()]
pattern = re.compile(r'(?<![A-Za-z0-9_/:.-])/(?:' + "|".join(re.escape(h) for h in hosts) + r')/')
def local_url(match):
    url = match.group(0)
    relative = re.sub(r"^https?://", "", url).split("?", 1)[0].split("#", 1)[0]
    candidate = source / unquote(relative)
    if candidate.is_dir():
        candidate /= "index.html"
    if candidate.is_file():
        suffix = url[len(re.sub(r"^https?://", "", url).split("?", 1)[0].split("#", 1)[0]) + len(url.split("://")[0]) + 3:]
        return "/" + candidate.relative_to(source).as_posix() + suffix
    return url

# The captured WordPress widgets must also work without remote plugin initialization.
static_widgets = r"""
<style>
.qodef-qi-tabs-horizontal {visibility:visible!important}
.qodef-qi-tabs-horizontal .elementor-invisible {visibility:visible!important}
.qodef-qi-tabs-horizontal [hidden] {display:none!important}
.qodef-qi-tabs-horizontal .elementor-portfolio {height:auto!important}
.qodef-qi-tabs-horizontal .elementor-portfolio-item {position:relative!important;top:auto!important;left:auto!important;transform:none!important}
</style>
<script>
(function () {
  document.querySelectorAll('.qodef-qi-tabs-horizontal').forEach(function (tabs) {
    const links = Array.from(tabs.querySelectorAll('.qodef-tabs-horizontal-navigation a'));
    const panels = Array.from(tabs.querySelectorAll('.qodef-tabs-horizontal-content'));
    function select(link) {
      panels.forEach(function (panel) {
        const active = '#' + panel.id === link.getAttribute('href');
        panel.hidden = !active;
        panel.style.display = active ? 'block' : 'none';
      });
      links.forEach(function (item) {
        item.closest('li').classList.toggle('ui-state-active', item === link);
        item.setAttribute('aria-selected', String(item === link));
      });
    }
    links.forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault(); event.stopImmediatePropagation(); select(link);
      }, true);
    });
    if (links.length) select(links[0]);
    tabs.querySelectorAll('.elementor-widget-portfolio').forEach(function (widget) {
      const filters = Array.from(widget.querySelectorAll('[data-filter]'));
      filters.forEach(function (filter) {
        filter.setAttribute('role', 'button');
        function apply(event) {
          event.preventDefault(); event.stopImmediatePropagation();
          const category = filter.dataset.filter;
          filters.forEach(function (item) {
            item.classList.toggle('elementor-active', item === filter);
            item.setAttribute('aria-pressed', String(item === filter));
          });
          widget.querySelectorAll('.elementor-portfolio-item').forEach(function (item) {
            item.hidden = category !== '__all' && !item.classList.contains('elementor-filter-' + category);
          });
        }
        filter.addEventListener('click', apply, true);
        filter.addEventListener('keydown', function (event) {
          if (event.key === 'Enter' || event.key === ' ') apply(event);
        }, true);
      });
    });
  });
})();
</script>
"""
count = 0
for path in target.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".json", ".svg"}:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = re.sub(r"https:/(?!/)", "https://", text)
        text = re.sub(r"http:/(?!/)", "http://", text)
        text = re.sub(r"https?://www\.h2arch\.com/[^\s\\\"'<>)]*", local_url, text)
        if path.suffix.lower() == ".html" and 'qodef-tabs-horizontal-content' in text:
            text = text.replace('</body>', static_widgets + '</body>')
        text = pattern.sub(lambda m: base + m.group(0), text)
        path.write_text(text, encoding="utf-8")
        count += 1
(target / ".nojekyll").touch()
assert (target / "index.html").is_file()
assert (target / "www.h2arch.com/projects/index.html").is_file()
print(f"Prepared {count} text files for {base}/")
