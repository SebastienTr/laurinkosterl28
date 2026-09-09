# Working on Laurine

## Language and audience

All produced content, filenames, new model labels, documentation and commit messages must be in English. Conversation with the owner may be in French. Keep the README welcoming to sailors: visuals, downloads, colours and assembly. Keep fabrication instructions in `docs/DEVELOPMENT.md` and all scripts in `tools/`.

## Non-negotiable model decisions

- Keep the hull full length. The horizontal hull/deck joint is intentional.
- Preserve the two backstays, separate window inserts and deck fittings, wooden tiller and trim, two washboards and sliding hatch unless the owner requests a change.
- Use stable paths. Git commits and release tags replace numbered generation directories.
- The delivered Blender file and the delivered `.3mf` must always describe the same printable geometry and face colours. A successful slice alone does not prove this.

## One complete delivery per model change

1. Start with `git status`; preserve work that is already present. Read this file and the development guide. State the intended model change and its checks.
2. Edit `model/Laurine_L28.blend`, or change the source geometry/generator intentionally. Do not overwrite direct Blender edits by regenerating from the base without checking which model is authoritative for the change.
3. Run `python3 tools/project.py prepare`. Use `--from-source` only when the intended change belongs to the base geometry or generator. Preparation exports the final model, renders it, builds and slices the 3MF, then compares geometry, colours and part inventories.
4. Inspect the candidate views in `build/previews/` and the plate preview in Bambu Studio. Check the requested detail, overall proportions, supports, colours and fit clearances. Do not claim a visual review without performing it. Visual review is part of the agent's work; it does not automatically require another user confirmation.
5. Run `python3 tools/project.py promote`. It refuses stale candidates, replaces the complete delivered set, writes `reports/delivery.json`, and removes intermediate files. Never copy isolated exports into the public folders or edit the delivery receipt by hand.
6. Update affected assembly instructions and estimates. Review the diff. Stage the model, 3MF, parts, colours, layout, previews, reports and fabrication changes together. Stage deletions too.
7. Run `python3 tools/project.py check --staged`, then make a focused English commit describing the result, for example `Fix the tiller fitting and regenerate the print project`. Never bypass the pre-commit hook or commit a knowingly inconsistent snapshot.
8. After an authorized push, check the GitHub delivery-consistency result and report the outcome and any remaining physical validation.

Documentation-only commits may reuse the existing delivery when its receipt still passes. Identical binary files do not need artificial changes. Changes to fabrication tools, profiles or source inputs require a new checked candidate, even when the output looks unchanged.

## Clean repository and private references

- Put all intermediate renders, logs, temporary scripts and trial exports in ignored `build/`. Remove them after a successful delivery. Use `python3 tools/project.py clean` to discard an abandoned candidate.
- Put personal photos, videos, scans and shopping/account notes in ignored `private/`. Never stage them, force-add them or embed them in public Blender or 3MF files. Do not delete private references during cleanup.
- Only reviewed model renders belong in `docs/images/`. The geometry exporter checks both public Blender files for embedded reference images, notes and linked libraries.
- Keep the Git tree free of backup files, obsolete exports and version folders. Do not use `--no-verify`. Do not rewrite published commits or move release tags to hide a mistake; fix it in a new coherent commit.
- Install the local guard with `python3 tools/project.py install-hook` in every new clone. GitHub Actions also checks the committed snapshot. Hooks are local configuration and do not install themselves when cloning.

## Honest validation

Automated checks cover file identity, the final-model export, triangle coordinates, face colours, part and plate inventories, slicing success and G-code checksums. They do not establish hydrodynamic accuracy, real filament colour, strength, physical fit or support removal. Describe those as untested until there is print evidence.
