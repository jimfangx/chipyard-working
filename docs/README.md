# Chipyard Docs

This directory is an Astro Starlight documentation project. The existing RST
files remain the source of truth. Before Astro starts or builds, the
`scripts/sphinx_to_starlight.py` bridge runs Sphinx and converts the rendered
article HTML into Starlight Markdown pages under `src/content/docs`.

## Local development

Activate or place the Chipyard conda environment on `PATH`, then install the
Node dependencies:

```sh
export PATH=/scratch/jfx/docs-exp/.conda-env/bin:$PATH
cd docs
npm ci
npm run dev
```

`npm run dev` starts a docs watcher and Astro. When an RST file or related
Sphinx source changes, the watcher reruns `scripts/sphinx_to_starlight.py`;
Astro serves the regenerated Starlight content without restarting.

The active environment must include the Python/Sphinx dependencies from either
`requirements.txt` or `../conda-reqs/docs.yaml`, because the Starlight build
starts by rendering the RST source with Sphinx. Read the Docs installs
`requirements.txt` with pip to avoid a slow conda solve, while local development
can use the docs conda environment. Node.js is provided separately by Read the
Docs via `.readthedocs.yml`, or by any local Node installation on `PATH`.

Build static docs:

```sh
cd docs
npm run build
```

## Versioned docs

Read the Docs owns production versioning. For each active RTD version, RTD
checks out the matching Git branch or tag, runs the Starlight build from that
checkout, and serves the generated static site at `/en/<version>/`.

The default production docs are RTD's `latest` version, which points at the
latest commit on the default branch. Release tags such as `1.14.0` and `1.13.0`
are separate RTD versions exposed through the Read the Docs version switcher.
The in-page Starlight version selector is populated by Read the Docs Addons, so
it appears on production RTD pages and stays hidden during local previews.

The Astro `base` path is set from `READTHEDOCS_LANGUAGE` and
`READTHEDOCS_VERSION` during RTD builds. For local testing of the same path
shape, set `DOCS_BASE`:

```sh
cd docs
DOCS_BASE=/en/latest npm run build
```

The generated Starlight content under `src/content/docs` and copied Sphinx
assets under `public/sphinx` are build artifacts and are ignored by Git.
