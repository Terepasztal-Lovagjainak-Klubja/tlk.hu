#!/usr/bin/env python3
"""Mirror public Google Drive folders into assets/images/gallery/<name>/.

The {{< gallery >}} shortcode (github.com/mfg92/hugo-shortcode-gallery) calls
resources.Match and .Resize, so it needs real files on disk — it cannot be handed
a URL. Drive is the upload inbox; Hugo still generates the thumbnails and serves
the files, so the live site never depends on Google.

Listing and downloading both go through gdown, which scrapes Drive's undocumented
embeddedfolderview endpoint. That is what buys us "no API key, no GCP project, no
repository secret". The trade-off is that the listing carries no md5 checksum, no
mime type and no pagination:

  * no checksum  -> we skip on filename, not content. Fine for photos, which get
                    added and deleted but effectively never edited in place.
  * no mime type -> we filter on file extension instead.
  * no pagination -> a big folder can be silently truncated. Set "minFiles" on a
                    gallery to turn that into a build failure instead of quietly
                    missing photos.

Nothing downloaded here is committed: assets/images/gallery/ is gitignored.

For each gallery this also writes content/product/<name>.md the first time it
sees that gallery, pre-filled with frontmatter and a {{< gallery >}} shortcode
pointing at the synced images. It never overwrites an existing content file —
that file is yours after creation, in case you add real copy to it.

Usage:
    python3 scripts/sync_drive_galleries.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import gdown
except ModuleNotFoundError:  # reported properly in main(), and only if needed
    gdown = None

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "galleries.json"
OUTPUT_ROOT = ROOT / "assets" / "images" / "product"
CONTENT_ROOT = ROOT / "content" / "product"

# Formats Hugo's image processing can actually read. HEIC is deliberately absent:
# Hugo cannot decode it, so an iPhone upload would break the build. Those files
# are reported as skipped rather than ignored, so someone notices and converts.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}

# Leading bytes of every format above. Checked after download so that an HTML
# interstitial or a rate-limit page can never be written into a .jpg, where it
# would fail much later as an unreadable-image build error.
MAGIC = (
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"GIF87a",
    b"GIF89a",
    b"II*\x00",  # TIFF, little endian
    b"MM\x00*",  # TIFF, big endian
    b"BM",  # BMP
)


def is_image_bytes(path: Path) -> bool:
    with path.open("rb") as handle:
        head = handle.read(16)
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return True
    return head.startswith(MAGIC)


def safe_name(drive_name: str, drive_id: str, taken: set[str]) -> str:
    """Flatten a Drive filename to a predictable ASCII one.

    Drive names are whatever someone's phone produced, in Hungarian, with spaces
    and accents. Hugo will process those but the URLs are a mess. NFD plus
    dropping combining marks covers á é í ó ö ő ú ü ű. The id suffix breaks ties
    deterministically, so two photos that flatten to the same name cannot
    silently overwrite each other.
    """
    suffix = Path(drive_name).suffix
    stem = drive_name[: -len(suffix)] if suffix else drive_name

    def flatten(text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
        return stripped.lower()

    slug = re.sub(r"[^a-z0-9]+", "-", flatten(stem)).strip("-") or "image"
    ext = re.sub(r"[^a-z0-9.]", "", flatten(suffix))

    name = f"{slug}{ext}"
    if name in taken:
        name = f"{slug}-{drive_id[:6].lower()}{ext}"
    taken.add(name)
    return name


def list_folder(folder_id: str) -> list[tuple[str, str]]:
    """Return [(drive_id, basename)] for everything in the folder, recursively."""
    entries = gdown.download_folder(
        id=folder_id,
        skip_download=True,
        quiet=True,
        use_cookies=False,
    )
    # skip_download hands back GoogleDriveFileToDownload(id, path, local_path);
    # path is prefixed with the Drive folder name, which we do not want to keep.
    return [(entry.id, Path(entry.path).name) for entry in entries or []]


def yaml_quote(text: str) -> str:
    """Double-quote a scalar for YAML frontmatter, escaping embedded quotes."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def title_from_name(name: str) -> str:
    """Fall back to a readable title if the gallery config doesn't set one."""
    words = re.split(r"[-_]+", name)
    return " ".join(w.capitalize() for w in words if w)


def hugo_date_now() -> str:
    """RFC3339 timestamp in the same shape Hugo's own archetypes produce."""
    now = datetime.now().astimezone()
    offset = now.strftime("%z")  # e.g. "+0200"
    offset = f"{offset[:3]}:{offset[3:]}"  # -> "+02:00"
    return now.strftime("%Y-%m-%dT%H:%M:%S.000") + offset


def write_content_page(gallery: dict, name: str, planned: list[tuple[str, str]]) -> str | None:
    """Create content/product/<name>.md the first time this gallery is seen.

    Returns a short status string for the summary line, or None if there was
    nothing to do (file already existed, or there are no images yet to build
    a thumbnail from).
    """
    target_path = CONTENT_ROOT / f"{name}.md"
    if target_path.exists():
        return None  # never overwrite — this file is yours once it exists

    if not planned:
        return "content page skipped (no images yet)"

    title = gallery.get("title") or title_from_name(name)
    thumbnail = f"images/product/{name}/" + min(fname for _, fname in planned)

    categories = gallery.get("categories") or gallery.get("category")
    if isinstance(categories, str):
        categories = [categories]
    categories_yaml = (
        "\n".join(f"  - {yaml_quote(c)}" for c in categories) if categories else ""
    )

    frontmatter = (
        "---\n"
        f"title: {yaml_quote(title)}\n"
        f"date: {hugo_date_now()}\n"
        f"thumbnail: {thumbnail}\n"
        "categories:"
        + (f"\n{categories_yaml}" if categories_yaml else "")
        + "\n"
        "---\n\n"
        "{{< gallery\n"
        '  globalMatch="images/product/' + name + '/*"\n'
        '  sortOrder="asc"\n'
        '  rowHeight="200"\n'
        '  margins="5"\n'
        '  thumbnailResizeOptions="600x600 q90 Lanczos"\n'
        '  previewType="blur"\n'
        "  embedPreview=true\n"
        "  loadJQuery=true\n"
        ">}}\n"
    )

    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    target_path.write_text(frontmatter, encoding="utf-8")
    return f"content page created ({target_path.relative_to(ROOT)})"


def sync_gallery(gallery: dict) -> str:
    name = gallery.get("name", "")
    folder_id = str(gallery.get("folderId", ""))
    min_files = gallery.get("minFiles")

    if not name or "/" in name or "\\" in name:
        raise ValueError(f"gallery name must be a single directory segment, got {name!r}")
    if not folder_id or folder_id.startswith("REPLACE"):
        raise ValueError(f'gallery "{name}" has no folderId set')

    # Accept a pasted folder URL as well as a bare id.
    match = re.search(r"/folders/([\w-]+)", folder_id)
    if match:
        folder_id = match.group(1)

    directory = OUTPUT_ROOT / name
    directory.mkdir(parents=True, exist_ok=True)

    listing = list_folder(folder_id)
    images = [(i, n) for i, n in listing if Path(n).suffix.lower() in IMAGE_SUFFIXES]
    skipped = [n for _, n in listing if Path(n).suffix.lower() not in IMAGE_SUFFIXES]

    # embeddedfolderview truncates large folders with no error and no page token,
    # so a gallery that quietly loses half its photos is the failure mode to guard
    # against. minFiles is the guard.
    if min_files is not None and len(images) < int(min_files):
        raise RuntimeError(
            f'gallery "{name}" returned only {len(images)} images but minFiles is '
            f"{min_files} — Drive's folder view has probably truncated the listing"
        )

    taken: set[str] = set()
    planned = [(drive_id, safe_name(n, drive_id, taken)) for drive_id, n in images]

    downloaded = 0
    for drive_id, target in planned:
        path = directory / target
        if path.exists():
            continue

        partial = path.with_suffix(path.suffix + ".part")
        result = gdown.download(
            id=drive_id,
            output=str(partial),
            quiet=True,
            use_cookies=False,
            retries=3,
        )
        if result is None or not partial.exists():
            partial.unlink(missing_ok=True)
            raise RuntimeError(f'failed to download "{target}" ({drive_id}) in "{name}"')

        if not is_image_bytes(partial):
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                f'"{target}" ({drive_id}) in "{name}" did not come back as an image — '
                "Drive probably served an interstitial or a rate-limit page"
            )

        partial.rename(path)
        downloaded += 1

    # Drive is the source of truth: anything else in the directory was deleted
    # upstream, and would otherwise linger forever in the warm CI cache.
    keep = {target for _, target in planned}
    removed = 0
    for existing in directory.iterdir():
        if existing.name not in keep:
            existing.unlink()
            removed += 1

    content_note = write_content_page(gallery, name, planned)

    note = f", {len(skipped)} non-image skipped" if skipped else ""
    if skipped:
        note += f" ({', '.join(sorted(skipped)[:5])}{'…' if len(skipped) > 5 else ''})"
    if content_note:
        note += f", {content_note}"
    return (
        f"  {name}: {len(planned)} image(s) — {downloaded} downloaded, "
        f"{len(planned) - downloaded} cached, {removed} removed{note}"
    )


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    galleries = config.get("galleries", [])

    if not galleries:
        print(f"No galleries configured in {CONFIG_PATH}; nothing to sync.")
        return 0

    if gdown is None:
        print(
            "error: gdown is not installed. Run:\n"
            "  pip install -r scripts/requirements.txt",
            file=sys.stderr,
        )
        return 1

    print(f"Syncing {len(galleries)} gallery folder(s) from Google Drive:")

    failures = []
    for gallery in galleries:
        try:
            print(sync_gallery(gallery))
        except Exception as error:  # noqa: BLE001 - one bad folder must not hide the rest
            failures.append(f"{gallery.get('name', '<unnamed>')}: {error}")

    if failures:
        joined = "\n  - ".join(failures)
        hint = ""
        if any("download_folder" in f or "permission" in f.lower() or "404" in f for f in failures):
            hint = (
                '\n\nCheck that each folder is shared "Anyone with the link -> Viewer"; '
                "Drive's folder view returns nothing useful otherwise."
            )
        print(
            f"error: {len(failures)} of {len(galleries)} galleries failed to sync:"
            f"\n  - {joined}{hint}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())