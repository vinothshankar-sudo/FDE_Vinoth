# Project: Fizzco Migration Assurance Hub (FDE assignment)

## Hard rules
- All data is SYNTHETIC. Never use real client or Tiger data, names, systems or numbers.
- Never write credentials, tokens or API keys into any file. Use environment variables.
- State clearly which output is AI-generated; a human reviews before it is committed.

## Coding conventions

### 1. Naming
- Use snake_case for functions, variables and file names.
- Use UPPER_SNAKE_CASE for constants.
- Prefix table names with `raw_` or `trusted_`.

### 2. Error handling
- Never use a bare `except`. Catch specific exceptions.
- Raise or log an error message that includes the failing input (file path, value or row).
- Never swallow an error silently.

### 3. Logging
- Use the `logging` module. Do not use `print`.
- Format: `%(asctime)s %(levelname)s %(name)s - %(message)s`
- Log the start of each step, the row count, and the end of each step.

## Workflow
- Plan first, then act, then verify (run the code or tests) before saying the work is done.
- Seed all randomness with `SEED = 42`.