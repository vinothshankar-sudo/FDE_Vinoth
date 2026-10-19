> **AI-generated document. All data is synthetic. A human must review it before it is committed.**

# Lineage: pl_fizzco_sell_in_load

## Purpose
Sell-in orders - SFTP to raw, then raw to trusted (synthetic)

## Parameters
| Name | Type | Default value |
|---|---|---|
| load_date | String | Not specified |

## Activity flow
| Order | Activity name | Type | Depends on | Source | Target |
|---|---|---|---|---|---|
| 1 | Copy_sell_in_to_raw | Copy | None | ds_sftp_fizzco_sell_in | ds_adls_fizzco_raw_sell_in (container fizzco-landing, folder raw/sell_in/) |
| 2 | Run_sell_in_transform | DatabricksNotebook | Copy_sell_in_to_raw (Succeeded) | Not specified (notebook parameter container = fizzco-landing) | Not specified |

## Lineage
| Layer | Container | Folder | Evidence activity |
|---|---|---|---|
| Source | Not specified (dataset ds_sftp_fizzco_sell_in) | Not specified | Copy_sell_in_to_raw |
| Raw | fizzco-landing | raw/sell_in/ | Copy_sell_in_to_raw |
| Trusted | Not specified | Not specified | Run_sell_in_transform |

ds_sftp_fizzco_sell_in -> fizzco-landing/raw/sell_in/ -> Not specified (trusted, via notebook /Fizzco/sell_in_transform)

## Notebook used
- Path: /Fizzco/sell_in_transform
- Parameters:
  - container = fizzco-landing
  - load_date = @pipeline().parameters.load_date

## Risks or observations
- Copy_sell_in_to_raw: container `fizzco-landing` and folder `raw/sell_in/` are hard-coded; the folder does not use load_date.
- Run_sell_in_transform: container `fizzco-landing` and notebook path are hard-coded.
- Run_sell_in_transform: trusted target is not specified in the pipeline JSON.
- Both activities: no retry or timeout policy specified.
- No failure-path (Failed/Completed) dependency handling and no alerting activity.
- Parameter load_date has no default value.
- No secrets found in the JSON.
