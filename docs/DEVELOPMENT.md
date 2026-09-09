# Working on the model

Most visitors only need the downloads and assembly guide. This page describes the optional fabrication tools.

## Where things live

| Folder | Purpose |
|---|---|
| `model/` | Reviewed, assembled Blender model |
| `print/` | Reviewed ten-plate 3MF, individual STL parts and fit tests |
| `docs/images/` | Model renders used in the guides |
| `source/` | Base hull geometry, triangle colour assignments, assembly layout and palette |
| `tools/` | One entry point and its supporting fabrication scripts |
| `profiles/` | A1 and provisional PLA slicing settings |
| `reports/` | Digital checks and slicing estimates for the published parts |
| `build/` | Ignored intermediate work; never a second version archive |
| `private/` | Ignored personal photographs, reference documents and local notes |

`source/base_geometry.blend` supplies the original hull surfaces used by the fabrication generator. It contains no reference photographs. Some internal source identifiers retain their original names because the geometry generator uses them; delivered parts and assembly labels are English.

Version 1 preserves the latest reviewed model. Stable filenames are intentional: use Git commits and release tags to revisit older work. Do not create numbered generation folders.

## Optional fabrication tools

The baseline was prepared with Blender 5.2.1 LTS and Bambu Studio 2.8.3.66 on macOS. Python packaging helpers use NumPy and SciPy. The existing `.3mf` and `.blend` do not require these helpers.

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
```

The single entry point is `tools/project.py`:

```sh
# Repackage and slice the reviewed STL and colour data.
.venv/bin/python tools/project.py package

# Rebuild geometry and preview renders from the base surfaces.
.venv/bin/python tools/project.py geometry

# Rebuild geometry, then package and slice those new exports.
.venv/bin/python tools/project.py all
```

Set `BLENDER_BIN` and `BAMBUSTUDIO_BIN` if the applications are not in their standard macOS locations. Outputs and logs stay in `build/`; these commands never start a print or replace the reviewed deliverables automatically.

After a geometry change, inspect the model and test pieces, compare dimensions and clearances, slice every plate, and review colour assignments. Copy only approved results to `model/`, `print/`, `source/colors/`, `source/palette.json`, `docs/images/` and the relevant reports. Keep the assembly layout in `source/assembly.json` in sync with exported part names. Create a Git commit for each reviewed change.

## Public-file checks

Keep `private/` ignored before adding any files. Check Blender for packed images, external images, linked libraries and embedded notes: personal references must not travel inside the model. Also inspect 3MF metadata for local paths. Only model renders belong in the public image folder.

Version 1's Blender cleanup preserved mesh coordinates, topology and transforms. STL mesh payloads were preserved; 3MF geometry and printer moves were preserved while the old generation label was replaced. These migration checks are recorded in `reports/` alongside the original geometry and slicing checks.

The model still needs its first complete physical test build. A clean mesh or successful slice is not a substitute for checking the printed fit and support removal.
