---
name: document-pipeline
description: Generate a Markdown lineage document from an ADF pipeline JSON file. Use when the user types /document-pipeline <path>, or asks to document, describe or trace the lineage of an ADF pipeline definition (files like pl_fizzco_<feed>_load.json).
---

# Document an ADF pipeline

Input: the path of an ADF pipeline JSON file, given by the user after the command (for example `/document-pipeline shared/fizzco_lake/adf/pl_fizzco_sell_in_load.json`).
If the user did not supply a path, ask for it before doing anything else.

## Steps

1. Read the JSON file at the given path. Use only that file as the source of facts.
2. Take `<pipeline_name>` from the pipeline `name` field (fall back to the file name without extension if absent).
3. Write the document to `shared/fizzco_lake/docs/lineage_<pipeline_name>.md` (create the folder if needed; overwrite the same file if it exists).
4. Reread the saved file and check every table, column, path and value appears in the JSON. Remove anything that does not.

## Rules

- Use only facts present in the JSON. If something is not in the file, write `Not specified`.
- Do not invent table names, column names, containers, folders or notebook parameters.
- Resolve dataset or linked-service references only by the names written in the JSON; do not guess their contents.
- Do not run the pipeline or any code. Do not write credentials or secrets into the document.

## Document structure

Start with this banner at the very top:

> **AI-generated document. All data is synthetic. A human must review it before it is committed.**

Then a title `# Lineage: <pipeline_name>` and these sections:

1. **Purpose**: one line, taken from the pipeline `description` field.
2. **Parameters**: table `Name | Type | Default value`, from `parameters`.
3. **Activity flow**: table `Order | Activity name | Type | Depends on | Source | Target`. Order follows the dependency chain (activities with no `dependsOn` first). Include dependency conditions (for example Succeeded) in "Depends on".
4. **Lineage**: show source -> raw -> trusted, with container and folder for each layer, as a short table (`Layer | Container | Folder | Evidence activity`) plus one arrow line. Use `Not specified` for any layer or location not in the JSON.
5. **Notebook used**: notebook path and the parameters passed (name and value or expression). If no notebook activity exists, write `Not specified`.
6. **Risks or observations**: bullet list of items evidenced in the JSON, such as hard-coded paths, containers, names or values; missing retry or timeout policy; no failure-path (`Failed` or `Completed` dependency) handling; no alerting activity; secrets in plain text. Cite the activity name for each.

## Final reply

Report the output file path and a one-line summary of anything marked `Not specified`.
