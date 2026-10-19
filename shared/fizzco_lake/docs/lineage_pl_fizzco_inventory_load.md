> **AI-generated document. All data is synthetic. A human must review it before it is committed.**

# Lineage: pl_fizzco_inventory_load

## Purpose
Inventory snapshots - SFTP to raw, then raw to trusted (synthetic)

## Parameters
| Name | Type | Default value |
|---|---|---|
| load_date | String | Not specified |

## Activity flow
| Order | Activity name | Type | Depends on | Source | Target |
|---|---|---|---|---|---|
| 1 | Copy_inventory_to_raw | Copy | None | ds_sftp_fizzco_inventory | ds_adls_fizzco_raw_inventory (container fizzco-landing, folder raw/inventory/) |
| 2 | Run_inventory_transform | DatabricksNotebook | Copy_inventory_to_raw (Succeeded) | Not specified (notebook parameter container = fizzco-landing) | Not specified |
| 3 | Archive_Landing_Files | Copy | Run_inventory_transform (Succeeded) | Not specified | container fizzco-raw-archive, folder inventory/ |

## Lineage
| Layer | Container | Folder | Evidence activity |
|---|---|---|---|
| Source | Not specified (dataset ds_sftp_fizzco_inventory) | Not specified | Copy_inventory_to_raw |
| Raw | fizzco-landing | raw/inventory/ | Copy_inventory_to_raw |
| Trusted | Not specified | Not specified | Run_inventory_transform |
| Archive | fizzco-raw-archive | inventory/ | Archive_Landing_Files |

ds_sftp_fizzco_inventory -> fizzco-landing/raw/inventory/ -> Not specified (trusted, via notebook /Fizzco/inventory_transform) ; archive: fizzco-raw-archive/inventory/

## Notebook used
- Path: /Fizzco/inventory_transform
- Parameters:
  - container = fizzco-landing
  - load_date = @pipeline().parameters.load_date

## Risks or observations
- Copy_inventory_to_raw: container `fizzco-landing` and folder `raw/inventory/` are hard-coded; the folder does not use load_date.
- Run_inventory_transform: container `fizzco-landing` and notebook path are hard-coded; trusted target not specified.
- Archive_Landing_Files: no inputs or outputs dataset references; source is not specified. Container `fizzco-raw-archive` and folder `inventory/` are hard-coded.
- All activities: no retry or timeout policy specified.
- No failure-path (Failed/Completed) dependency handling and no alerting activity.
- Parameter load_date has no default value.
- No secrets found in the JSON.
