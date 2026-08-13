# Mandatory execution contract

Treat the supplied project as an authoritative, already validated tutorial
asset. Follow these requirements before the chapter-specific request:

1. Use only the versions in VERSIONS.md and the supplied lock/config files.
   Do not upgrade, downgrade, substitute, or remove a pinned dependency.
2. Do not regenerate, replace, rescale, or rearrange fixed worlds, models,
   trajectories, maps, images, or configuration assets.
3. Use only the documented tutorial entry script and its documented
   parameters. Do not invent an alternative installation or launch path.
4. Do not install into system Python, user site-packages, Miniconda, or
   unrelated environments. Project-local environments and the supplied
   container are the only allowed targets.
5. Do not disable checksum, schema, test, safety, or acceptance checks.
6. Do not edit files unless the chapter request explicitly asks for an edit.
   Before any edit, list the exact files and reason. Keep all other files
   byte-identical.
7. If a requirement conflicts with the machine or project, stop and report
   the observed command, sanitized error, and conflicting requirement.
   Do not work around it by changing versions, models, APIs, or assets.
8. Never print or store API keys, full environment dumps, usernames,
   hostnames, private paths, private network addresses, or unrelated data.
9. A task is complete only when the documented entry command and acceptance
   checks pass. Report exact commands, sanitized version lines, acceptance
   markers, and changed files. Do not infer success from process startup.
10. Keep commands bounded. For continuous applications, use the documented
    duration or shutdown command and leave no tutorial processes running.
11. An acceptance marker counts only when it is observed in command output or
    a generated runtime log. Finding the same text in source code is not
    runtime evidence.
12. If the entry is launched in the background, wait for that exact process to
    exit and inspect its final output before deciding PASS or FAIL.

Before running anything, reply with:

- the authoritative versions you found;
- the single entry command and parameters you will use;
- files you expect to change, including generated files;
- acceptance markers you will verify.

If any of those items are unclear, stop and ask for clarification.
