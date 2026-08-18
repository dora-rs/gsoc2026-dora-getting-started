# Multimodal pick-and-place asset guide

Use the supplied Habitat scene, trajectory, Dora dataflow, contracts, local
VLM configuration, and run.sh unchanged. Ensure Ollama is already serving the
pinned `qwen3-vl:8b-instruct` model.

The only entry command is:

```bash
OLLAMA_MODEL=qwen3-vl:8b-instruct bash run.sh
```

Do not invoke individual Python files, micromamba, Dora, Ollama APIs, or test
runners as an alternative path. Do not alter the confidence threshold,
trajectory, model, or structured JSON contract.

Success requires focused tests to pass, `TASK_SUCCESS` in
`outputs/logs/dora-run.log`, and
`Verified: complete Dora vision-gated task succeeded.` on stdout. Generated
paths are limited to local tools/environments, outputs, and Dora runtime state.
