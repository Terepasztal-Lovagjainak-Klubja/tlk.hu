# tlk.hu

The website of **Terepasztal Lovagjainak Klubja** — Budapest's and Hungary's
oldest wargame / board game / roleplaying game club. Published at
[tlk.hu](https://tlk.hu/).

A [Hugo](https://gohugo.io/) static site built on the
[Corporio](https://github.com/AminZibayi/Corporio) theme. The site content is in
Hungarian; code, config and docs are in English.

## Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Hugo | **0.139.0, extended** | The extended build is required for SCSS. See the version note below. |
| Node.js | >= 22 | Bootstrap, jQuery, Font Awesome and the PostCSS toolchain. |
| pnpm | 11 | Package manager — the repo has a `pnpm-lock.yaml`, not an npm one. |
| Go | >= 1.26 | Hugo modules are Go modules, and this site imports one. |
| Python | >= 3.10 | Only for the Drive gallery sync — or install [uv](https://docs.astral.sh/uv/) instead and skip it. See [Galleries](#galleries). |

**On the Hugo version:** it is pinned in `mise.toml`. Don't bump it casually —
`go.mod` pins `hugo-shortcode-gallery` to v1.3.0 because v1.4.0+ requires Hugo
>= 0.156.0, so the two move together.

If you use [mise](https://mise.jdx.dev/), the pinned Hugo is installed with:

```sh
mise install
```

Otherwise install Hugo **extended** 0.139.0 by hand — a newer Hugo will fail
(see Troubleshooting).

## Getting started

The Corporio theme is a git submodule, so clone recursively:

```sh
git clone --recurse-submodules https://github.com/Terepasztal-Lovagjainak-Klubja/tlk.hu.git
cd tlk.hu
```

Already cloned without it? Fix it with:

```sh
git submodule update --init --recursive
```

Then install the Node dependencies and start the dev server:

```sh
pnpm install
pnpm start
```

The site is now on <http://localhost:1313/>, rebuilding as you edit.

`pnpm install` is not optional: `config/_default/module.yaml` mounts the Font
Awesome and `@hyas/images` assets straight out of `node_modules`, and Hugo Pipes
resolves the SCSS/JS imports and the `postcss-cli` binary from there too. Hugo
fetches the `hugo-shortcode-gallery` module itself on first build, which is what
the Go toolchain is for.

## Commands

| Command | What it does |
| --- | --- |
| `pnpm start` | Dev server on <http://localhost:1313/> with live reload. |
| `pnpm dev` | Sync the Drive galleries, then start the dev server. |
| `pnpm build` | Production build (`hugo --gc --minify`) into `public/`. |
| `pnpm sync:galleries` | Mirror the Google Drive gallery folders into `assets/`. See [Galleries](#galleries). |
| `pnpm clean` | Delete `public/` and `resources/`. |

## Layout

```
config/_default/   Base config, params, menus, module mounts
config/production/ Production overrides (baseURL: https://tlk.hu/)
content/           Markdown: blog posts (yearly beszámolók), contact, gallery
data/              Homepage sections (YAML) + galleries.json (Drive folder list)
layouts/           Templates and shortcodes; override the theme from here
assets/            SCSS and JS processed by Hugo Pipes
scripts/           Build-time helpers (the Drive gallery sync)
static/            Files copied verbatim (favicons, images, fonts)
themes/corporio/   Theme, as a git submodule
```

The homepage is one long page assembled from the `data/*.yml` section files —
edit those to change the front page, not `content/_index.md`.

## Galleries

Galleries are rendered by the `{{< gallery >}}` shortcode from
[hugo-shortcode-gallery](https://github.com/mfg92/hugo-shortcode-gallery), which
resizes local image files. There are two ways to feed it.

**Committed images** — put them under `assets/images/product/<name>/` and point
the shortcode at them. This is what `content/product/festegetes_galeria.md` does.
Fine for a handful of images; the repo is already ~140 MB of photos, so prefer
Drive for anything new.

**Google Drive** — the club drops photos into a shared Drive folder, and CI
mirrors that folder into `assets/images/gallery/<name>/` before the Hugo build.
Hugo still generates the thumbnails and serves the files, so the live site never
depends on Google. Nothing downloaded is committed: `assets/images/gallery/` is
gitignored.

### Adding a Drive gallery

1. In Drive, share the folder **Anyone with the link → Viewer**. Without this the
   sync gets a 404.
2. Add an entry to `data/galleries.json`:

   ```json
   { "galleries": [
     { "name": "kirandulas-2026", "folderId": "1AbC...",
       "title": "Kirándulás 2026", "minFiles": 120 }
   ] }
   ```

   `folderId` accepts the bare id or the whole folder URL. `minFiles` is optional
   but worth setting on any large gallery — see [the truncation
   caveat](#the-one-real-risk-truncation).
3. Add a content page whose body uses the matching `globalMatch`:

   ```markdown
   ---
   title: Kirándulás 2026
   thumbnail: images/product/thumbnail_fest.jpg
   ---

   {{< gallery globalMatch="images/gallery/kirandulas-2026/*" sortOrder="asc"
     rowHeight="200" margins="5" thumbnailResizeOptions="600x600 q90 Lanczos"
     previewType="blur" embedPreview=true loadJQuery=true >}}
   ```

   The `thumbnail` front matter is **required** for pages under `content/product/`
   — `layouts/product/list.html` and the homepage product section call `.Resize`
   on it without a nil check and will fail the build if it is missing.
4. Push. The publish workflow syncs and deploys.

### No credentials required

`scripts/sync_drive_galleries.py` uses [gdown](https://github.com/wkentaro/gdown),
which reads Drive's public `embeddedfolderview` endpoint directly. **There is no
API key, no GCP project and no repository secret** — nothing to rotate, and
nothing that dies when whoever set it up leaves the club. Public sharing on the
folder is the only requirement.

`gdown` is pinned in `scripts/requirements.txt` on purpose: it scrapes an
undocumented endpoint, so it is the part of the build most likely to break when
Google changes something. Bump it deliberately and check that a gallery still
fills up afterwards.

### Previewing galleries locally

The sync is an ordinary command — GitHub Actions is not involved:

```sh
pnpm dev                # sync from Drive, then start the dev server
pnpm sync:galleries     # just the sync
pnpm build              # full production build, to check it end to end
```

`pnpm sync:galleries` sorts out Python by itself. If [uv](https://docs.astral.sh/uv/)
is installed it uses that — no virtualenv, and it provisions its own interpreter.
Otherwise it creates `.venv/` in the repo and installs there. Either way nothing
is added to your system Python, which would fail anyway on any Python new enough
to enforce PEP 668.

Run the sync once and the images land in `assets/images/gallery/<name>/`; after
that `pnpm start` behaves like any other content change. You only need to re-run
it to pick up new photos.

**Testing the layout without touching Drive:** the sync is the only thing that
writes to `assets/images/gallery/`, so you can drop a handful of JPEGs into
`assets/images/gallery/<name>/` by hand and point a page at them. The directory
is gitignored, so nothing gets committed. Just remember the next sync **deletes**
anything that is not in the Drive folder.

### How the sync behaves

- Skips files that are already present **by filename**. The folder view carries no
  checksum, so an edited photo kept under the same name will not be re-fetched —
  rename it in Drive to force a refresh. Photos get added and deleted far more
  often than edited in place, so this is a cheap trade.
- Deletes local files that are gone from Drive.
- Flattens filenames to ASCII (`Kőszegi vár.JPG` → `koszegi-var.jpg`) and breaks
  collisions with a short file-id suffix, so two photos can never overwrite one
  another.
- Ignores anything that is not a format Hugo can decode, and **names what it
  skipped** in the log. Watch for `.heic` — iPhone uploads land as HEIC, which
  Hugo cannot read; convert them to JPEG in Drive.
- Verifies each download really is image bytes, so a Drive interstitial or
  rate-limit page never gets written into a `.jpg`.
- Fails loudly, per gallery, listing which ones broke. A failed publish leaves the
  previous deploy live.

### The one real risk: truncation

Drive's public folder view returns a single HTML page with **no pagination**, and
it truncates large folders without any error. A gallery quietly showing 200 of 340
photos is the failure mode to watch for.

`minFiles` is the guard: set it a little below the real photo count and the build
fails instead of silently dropping pictures. Set it on anything large.

If you hit the ceiling on a folder, the fixes are to split it into several smaller
folders (one gallery entry each), or to switch the listing back to the Drive API,
which does paginate — that needs an API key, which is exactly what this setup
avoids.

Photos added to Drive go live on the next push, on a manual **Run workflow**, or
on the nightly `schedule:` in `publish.yaml` — GitHub delays scheduled runs under
load and disables them after 60 days of repo inactivity, so treat the nightly run
as best effort.

CI (`ci.yaml`) deliberately does *not* sync: it only checks that the site builds,
and an empty gallery directory renders fine.

## Environments

Hugo layers `config/<environment>/` over `config/_default/`:

- `pnpm start` uses **development** — baseURL `http://localhost:1313/`
- `pnpm build` uses **production** — baseURL `https://tlk.hu/`

## CI and deployment

- `.github/workflows/ci.yaml` — builds on every push and pull request.
- `.github/workflows/publish.yaml` — builds `main` and deploys it to GitHub
  Pages. The deploy overrides the baseURL with the URL Pages actually serves
  from, so it stays correct whether or not the custom domain is configured.
  It also mirrors the Drive galleries before building (see
  [Galleries](#galleries)) and runs nightly to pick up new photos — no secrets
  are configured or needed. Two rolling caches keep that cheap:
  `assets/images/gallery` (the downloads) and `resources` (Hugo's generated
  thumbnails).

## Troubleshooting

**`failed to decode "caches": "getjson" is not a valid cache name`**

You are running a Hugo newer than 0.139.0 — most likely one on your `PATH`
shadowing the pinned one. Check with `mise which hugo`; if mise is installed but
not active in your shell, add `eval "$(mise activate zsh)"` to your `~/.zshrc`.

**Missing styles, or `Could not resolve "lazysizes"` / `File to import not
found: bootstrap/scss/functions`**

`node_modules` is missing or stale. Run `pnpm install`.

**The theme's templates seem to be missing**

The `themes/corporio` submodule was not checked out. Run
`git submodule update --init --recursive`.
