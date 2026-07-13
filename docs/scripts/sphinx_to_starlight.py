#!/usr/bin/env python3
"""Generate Starlight Markdown pages from the existing Sphinx/RST docs."""

from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


DOCS_ROOT = Path(__file__).resolve().parents[1]
SPHINX_BUILD = DOCS_ROOT / "_build" / "starlight-sphinx-html"
CONTENT_ROOT = DOCS_ROOT / "src" / "content" / "docs"
PUBLIC_ROOT = DOCS_ROOT / "public" / "sphinx"
MANIFEST_NAME = ".sphinx-generated.json"
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-subdir", default="", help="Subdirectory under src/content/docs to write into.")
    parser.add_argument("--asset-subdir", default="current", help="Subdirectory under public/sphinx to write assets into.")
    parser.add_argument("--skip-sphinx", action="store_true", help="Reuse the existing Sphinx HTML build.")
    args = parser.parse_args()

    target_root = CONTENT_ROOT / args.target_subdir
    asset_prefix = f"sphinx/{args.asset_subdir}"

    if not args.skip_sphinx:
        build_sphinx()

    copy_assets(args.asset_subdir)
    clean_generated(target_root)
    generated = convert_pages(target_root, asset_prefix)
    write_manifest(target_root, generated)

    print(f"Generated {len(generated)} Starlight pages in {target_root.relative_to(DOCS_ROOT)}")
    return 0


def build_sphinx() -> None:
    env = os.environ.copy()
    env.setdefault("SKIP_URL_CHECK", "1")
    SPHINX_BUILD.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "html", str(DOCS_ROOT), str(SPHINX_BUILD), "-q"],
        cwd=DOCS_ROOT,
        env=env,
        check=True,
    )


def copy_assets(asset_subdir: str) -> None:
    dest = PUBLIC_ROOT / asset_subdir
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("_static", "_images"):
        src = SPHINX_BUILD / name
        if src.exists():
            shutil.copytree(src, dest / name)


def clean_generated(target_root: Path) -> None:
    manifest = target_root / MANIFEST_NAME
    if not manifest.exists():
        return
    for rel in json.loads(manifest.read_text(encoding="utf-8")):
        path = target_root / rel
        if path.exists():
            path.unlink()
    for path in sorted(target_root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def convert_pages(target_root: Path, asset_prefix: str) -> list[str]:
    generated: list[str] = []
    for html_path in sorted(SPHINX_BUILD.rglob("*.html")):
        rel_html = html_path.relative_to(SPHINX_BUILD)
        if rel_html.parts[0].startswith("_") or rel_html.name in {"genindex.html", "py-modindex.html", "search.html"}:
            continue

        page = html_path.read_text(encoding="utf-8")
        body = extract_article_body(page, html_path)
        body = rewrite_links(body, rel_html.as_posix(), asset_prefix)
        title = extract_title(body, page, rel_html)

        out_rel = rel_html.with_suffix(".md")
        out_path = target_root / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_markdown(title, body), encoding="utf-8")
        generated.append(out_rel.as_posix())
    return generated


def extract_article_body(page: str, html_path: Path) -> str:
    match = re.search(r"<div\s+itemprop=[\"']articleBody[\"'][^>]*>", page)
    if not match:
        raise RuntimeError(f"Could not find Sphinx article body in {html_path}")

    depth = 1
    pos = match.end()
    tag_re = re.compile(r"<!--.*?-->|</?([a-zA-Z][\w:-]*)(?:\s[^<>]*?)?>", re.DOTALL)
    for tag_match in tag_re.finditer(page, pos):
        token = tag_match.group(0)
        tag = (tag_match.group(1) or "").lower()
        if not tag:
            continue
        if token.startswith("</"):
            if tag == "div":
                depth -= 1
                if depth == 0:
                    return page[pos : tag_match.start()].strip()
        elif tag == "div" and not token.endswith("/>"):
            depth += 1

    raise RuntimeError(f"Could not find end of Sphinx article body in {html_path}")


def extract_title(body: str, page: str, rel_html: Path) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.DOTALL)
    if h1:
        return clean_text(h1.group(1))
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.DOTALL)
    if title:
        return clean_text(title.group(1).split(" — ")[0].split(" &mdash; ")[0])
    return rel_html.with_suffix("").name.replace("-", " ")


def clean_text(value: str) -> str:
    value = re.sub(r"<a class=[\"']headerlink[\"'].*?</a>", "", value, flags=re.DOTALL)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return " ".join(value.split())


def render_markdown(title: str, body: str) -> str:
    frontmatter = {
        "title": title,
        "template": "doc",
    }
    yaml = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items())
    return f"---\n{yaml}\n---\n\n<div class=\"sphinx-page\">\n\n{body}\n\n</div>\n"


def rewrite_links(body: str, current_html: str, asset_prefix: str) -> str:
    attr_re = re.compile(r"(?P<attr>href|src)=(?P<quote>[\"'])(?P<url>.*?)(?P=quote)")

    def replace(match: re.Match[str]) -> str:
        url = html.unescape(match.group("url"))
        rewritten = rewrite_url(url, current_html, asset_prefix)
        return f'{match.group("attr")}={match.group("quote")}{html.escape(rewritten, quote=True)}{match.group("quote")}'

    return attr_re.sub(replace, body)


def rewrite_url(url: str, current_html: str, asset_prefix: str) -> str:
    split = urlsplit(url)
    if split.scheme or split.netloc or split.path.startswith("/") or split.path == "":
        return url
    if split.path.startswith("#") or split.path.startswith(("mailto:", "javascript:")):
        return url

    current_dir = posixpath.dirname(current_html)
    normalized = posixpath.normpath(posixpath.join(current_dir, split.path))

    if normalized.startswith("_static/") or normalized.startswith("_images/"):
        current_route = html_path_to_route(current_html)
        asset_route = f"{asset_prefix}/{normalized}"
        rel = posixpath.relpath(asset_route, current_route or ".")
        return urlunsplit(("", "", rel, "", split.fragment))

    if normalized.endswith(".html"):
        route = html_path_to_route(normalized)
        current_route = html_path_to_route(current_html)
        rel = posixpath.relpath(route or ".", current_route or ".")
        if rel == ".":
            rel = "."
        rel = rel.rstrip("/") + "/"
        return urlunsplit(("", "", rel, "", split.fragment))

    return url


def html_path_to_route(path: str) -> str:
    without_ext = path[:-5] if path.endswith(".html") else path
    if without_ext == "index":
        return ""
    if without_ext.endswith("/index"):
        return without_ext[: -len("/index")].lower()
    return without_ext.lower()


def write_manifest(target_root: Path, generated: list[str]) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    (target_root / MANIFEST_NAME).write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
