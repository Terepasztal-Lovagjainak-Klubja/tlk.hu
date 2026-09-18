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
| `pnpm build` | Production build (`hugo --gc --minify`) into `public/`. |
| `pnpm clean` | Delete `public/` and `resources/`. |

## Layout

```
config/_default/   Base config, params, menus, module mounts
config/production/ Production overrides (baseURL: https://tlk.hu/)
content/           Markdown: blog posts (yearly beszámolók), contact, gallery
data/              YAML driving the homepage sections (hero, about, service, …)
layouts/           Templates and shortcodes; override the theme from here
assets/            SCSS and JS processed by Hugo Pipes
static/            Files copied verbatim (favicons, images, fonts)
themes/corporio/   Theme, as a git submodule
```

The homepage is one long page assembled from the `data/*.yml` section files —
edit those to change the front page, not `content/_index.md`.

## Environments

Hugo layers `config/<environment>/` over `config/_default/`:

- `pnpm start` uses **development** — baseURL `http://localhost:1313/`
- `pnpm build` uses **production** — baseURL `https://tlk.hu/`

## CI and deployment

- `.github/workflows/ci.yaml` — builds on every push and pull request.
- `.github/workflows/publish.yaml` — builds `main` and deploys it to GitHub
  Pages. The deploy overrides the baseURL with the URL Pages actually serves
  from, so it stays correct whether or not the custom domain is configured.

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
