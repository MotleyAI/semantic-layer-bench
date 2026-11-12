<!-- anfra:begin -->
## anfra

This is an anfra repo.

- Use the anfra skills for work in this repo. They know anfra's languages and commands, so you'll work more
  accurately and efficiently with them than from memory.
- Check a command with `anfra <command> --help` rather than guessing; `anfra --help` lists the commands.
  Before scripting a call or reading its result, `--schema` gives its exact input and output
  (`--schema --jq '.output | del(.. | .description?)'`: the output alone, without descriptions).
- anfra commands write their answer to stdout: most as a YAML document, a few for a person. To get it structured,
  pass `--yaml` (or `--json`). To avoid any question or interaction, pass `--non-interactive`: a command that
  would ask fails instead. Warnings and errors go to stderr as YAML documents (JSONL with `--json`), each with a
  `code` to act on, and a failed command exits non-zero.
- `anfra status` gives the logs' location (`repo.logs`). There you find the server's and the apps' logs,
  errors included, which help when building and debugging.
- Docs: anfra at https://anfra.ai/docs, AML and AQL at https://amql.org/docs.

Keeping the skills working:

- Once per session, before your first anfra command, run `anfra version --skills <version>`, with the version
  from the `anfra skills` line at the end of an anfra skill you've loaded, or `--skills unknown` if it has no such
  line. Follow the hints it prints. If anfra doesn't know `--skills`, it's out of date: ask the user to run
  `anfra update`.
- If the anfra skills aren't available to you, run `anfra agent setup --agent <your id>` and follow what it says,
  then ask the user to restart you. If that fails, install them as https://github.com/holistics/anfra-skills says
  for the agent you are.
<!-- anfra:end -->
