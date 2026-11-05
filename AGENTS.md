# Unified skills repository

- Communicate with the user in Chinese and with tools in English. Keep explanations direct and natural.
- This is one Git repository containing five source packages and six skills. Child directories are packages, not separate Git checkouts. The five original GitHub repositories were deleted after verified local history backups; use this repository for maintenance and distribution.
- `skills.json` declares skill IDs, runtime resources, platforms, and dependencies. Preserve skill IDs, file names, and invocation commands unless the user requests a migration.
- Read a package's own `AGENTS.md` and protocol before changing its source. Keep shared `SKILL.md` instructions consistent across supported platforms.
- Edit sources here and use `python3 manage.py sync` to update platform installations. Run `python3 manage.py check` afterwards. Platform copies are generated outputs.
- Run `python3 scripts/check_workspace.py` after changing packaging, shared management code, or behavior spanning packages. For a localized change, run the relevant package checks.
- `source-lock.json` records the imported source commits and file hashes, including explicitly included uncommitted changes. It documents the initial import; subsequent changes are tracked by this repository's Git history. Its original URLs are historical records. `source-retirement.json` and `docs/legacy-repositories.md` record the retirement and recovery details.
- Keep real requirements, customer data, reports, local state, and runtime caches outside Git. Put business inputs and outputs in the business project's working directory.
- `.state/` contains durable installation backups. Preserve existing backup data unless removing it is part of the user's request.
- Original standalone installers remain available in each source package. Keep their declared behavior compatible when changing installation resources.
