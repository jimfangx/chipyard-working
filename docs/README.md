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

The active environment must include the Python/Sphinx dependencies from
`../conda-reqs/docs.yaml`, because the Starlight build starts by rendering the
RST source with Sphinx. Node.js is provided separately: Read the Docs installs
it via `.readthedocs.yml`, and local development can use an activated conda env,
system Node, or another Node installation on `PATH`.

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
