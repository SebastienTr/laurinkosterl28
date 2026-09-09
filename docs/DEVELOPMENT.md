# A clean, coherent model delivery

Visitors can print the published project without running any scripts. This guide is for working on the model. The collaboration rules are in [AGENTS.md](../AGENTS.md).

## Set up once

The fabrication tools use Blender, Bambu Studio and Python with NumPy and SciPy. The current baseline uses Blender 5.2.1 and Bambu Studio 2.8.3.66 on macOS.

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
python3 tools/project.py install-hook
```

Set `BLENDER_BIN` and `BAMBUSTUDIO_BIN` if the applications are elsewhere. The commit check uses only Python's standard library; Blender and the slicer are needed when preparing a delivery, not for every documentation commit.

## Prepare → review → promote → commit

All commands go through `tools/project.py`.

```sh
# Export the edited final Blender model, render, package, slice and compare.
.venv/bin/python tools/project.py prepare

# Alternatively, deliberately regenerate from the base geometry and generator.
.venv/bin/python tools/project.py prepare --from-source
```

The default uses `model/Laurine_L28.blend` as the model to deliver. The source option builds from `source/base_geometry.blend` and applies the finishing step **before** the final export. It is not appropriate for preserving manual changes made only to the delivered Blender file.

Each part's orientation is recorded in `source/print_layout.json`. The assembled model is exported into its printing orientation, in millimetres. STL coordinates and the coloured triangles in the sliced 3MF are compared with that final export. The assembly layout must include every part on its intended plate, with the correct number of copies. Failed checks stop preparation.

Review `build/previews/` and open `build/bambu/Laurine_Multicolor_A1.3mf` in Bambu Studio. Inspect the changed detail and the full boat; review colours, orientations, supports and clearances. The tools cannot judge whether a pulpit looks like the real boat.

```sh
# After the visual review, replace the full delivery and remove temporary files.
.venv/bin/python tools/project.py promote

# Review and stage all related changes and deletions, then check the actual index.
git diff --stat
git add -A
python3 tools/project.py check --staged
git commit -m "Describe the model change and its updated print project"
```

Promotion checks that neither the inputs nor the candidate files changed since preparation. It replaces whole export directories so removed parts cannot linger. The receipt is written last: an interrupted promotion cannot pass the commit guard with a stale receipt. If it fails, prepare and review again.

The receipt records SHA-256 hashes of the Blender model, 3MF, exports, colours, layouts, profiles, fabrication tools, reports and previews. The hook reads **the Git index**, so an unstaged new receipt cannot accidentally validate a different staged model. Ordinary README or assembly-text changes do not require regenerating unchanged binaries.

GitHub Actions repeats the committed-file check and runs regression checks for missing parts, altered models, extra exports, private files and partially staged deliveries. Do not bypass a failure. These are accidental-drift safeguards, not proof against someone deliberately rewriting the checks and receipt. Repository administrators can still bypass local hooks; server-side branch protection is a separate repository setting.

## Where files belong

| Folder | Contents |
|---|---|
| `model/` | The final assembled Blender model |
| `print/` | Matching 3MF, individual STL parts and fit tests |
| `source/` | Base geometry, print orientations, assembly layout, palette and exported triangle colours |
| `tools/` | The single command entry point and its helpers |
| `profiles/` | Printer and provisional PLA settings |
| `docs/images/` | Renders from the delivered model |
| `reports/` | Current geometry, project, material-use and delivery checks |
| `build/` | Ignored candidates and temporary work; removed on promotion |
| `private/` | Ignored personal references; never cleaned with build outputs |

Some internal base-geometry identifiers retain their original names because the generator uses them. New labels and delivered parts are in English.

Use `python3 tools/project.py clean` to discard an abandoned candidate. A failed preparation can leave its logs for diagnosis; they remain ignored and must be cleaned before reporting a finished delivery. Never put trial scripts or exports at the repository root.

## Commits and releases

Make one focused commit for a model change and its complete print delivery. Prefer a concrete message such as `Refine the stern pushpit and regenerate the print project`. Keep unrelated edits separate. Use Git history instead of generation folders.

A commit does not silently replace an existing release. Published tags and downloads remain fixed snapshots. When making a new public release, update `VERSION`, prepare and verify the delivery, commit it, create a new tag and package downloads from that exact commit. Refresh the README download links for that release.

No automated check replaces the first physical test print. Keep fit, strength, real colour matching and support removal clearly marked as untested until demonstrated.
