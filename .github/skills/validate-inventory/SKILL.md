---
name: validate-inventory
description: Validate an application object inventory CSV before cutover. Use whenever the user asks to check, validate, review or audit an inventory, object list, object register or lineage sheet, including casual phrasing such as "check the inventory for problems", "is the object list OK?" or "sanity check the register". Checks columns vs template, unique object_id, depends_on references, object_type and status values.
---

# Validate inventory

Checks an inventory CSV against five rules: R1 columns match the template in order, R2 `object_id` is unique, R3 every `depends_on` exists as an `object_id`, R4 `object_type` is Pipeline/Notebook/Table, R5 `status` is Active/Retired. Expected columns are read at runtime from `shared/inventory/App_Object_Inventory_Template.csv`.

## Steps

1. **Locate the inventory CSV.** If the user gave a path, use it. Otherwise search for inventory CSVs (for example under `shared/inventory/`, excluding the template). Ask which file only if more than one candidate exists; do not ask if there is exactly one.
2. **Run the validator** from the repository root:
   ```
   python3 .github/skills/validate-inventory/validate_inventory.py <path_to_inventory.csv>
   ```
   Exit code 0 = PASS, 1 = FAIL, 2 = file could not be read (error is logged to stderr).
3. **Show the result exactly as printed:** the violations table and the final `PASS` or `FAIL` line, unmodified. If the exit code is 2, show the logged error instead. State that the output is tool-generated and a human should review it.
4. **Never edit the inventory file.** Only propose fixes if the user asks for them, and do not apply them unless explicitly told to.
