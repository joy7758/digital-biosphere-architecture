# Demo Results Snapshot

This page is intended for poster, QR, and handout screenshots.

Workflow:
`DPP Object -> Agent Result -> Audit Record -> MVK Input -> Public Evidence Summary`

Screenshot targets:
- [Input object](../input/dpp_passport_sample.json)
- [Public evidence summary](../output/public_evidence_summary.json)
- [Runnable demo README](../README.md)

## Input Object

```json
{
  "batch_id": "BATCH-2026-001",
  "carbon_record": {
    "unit": "kgCO2e",
    "value": 12.4
  },
  "compliance_task": "generate_audit_ready_summary",
  "manufacturer": "RedRock Demo Factory",
  "material": "LFP",
  "object_id": "DPP-DEMO-0001",
  "origin_country": "CN",
  "product_name": "Demo Battery Module"
}
```

## Public Evidence Summary

```json
{
  "architecture_repo": "https://github.com/joy7758/digital-biosphere-architecture",
  "demo_handle": "21.T11966/aro-audit-demo-do-1",
  "generated_files": [
    {
      "path": "output/agent_result.json",
      "sha256": "7c3705f213505dc3e144b2a998dbfab9b34627b9167a51d546a0cc6bc2b160dc"
    },
    {
      "path": "output/aro_audit_record.json",
      "sha256": "441b34d0722148db8fad913a4b2cd392cb81fe9ee650dc03f72fa740d800e8c6"
    },
    {
      "path": "output/mvk_input.json",
      "sha256": "f62a495d35536811b472a07a9a903f3c751859db7da3bb59ce0c7c95742e1720"
    }
  ],
  "mvk_repo": "https://github.com/joy7758/fdo-kernel-mvk",
  "paper_doi": "10.5281/zenodo.18501430",
  "profile_handle": "21.T11966/aro-audit-profile-v1",
  "spec_url": "https://github.com/joy7758/aro-audit/blob/main/docs/aroaudit-profile-v1.md"
}
```

## Verified Run

```text
$ make all
rm -f output/*.json
python3 scripts/run_demo.py
DEMO_BUILD_OK
python3 scripts/verify_demo.py
VERIFY_PASS
```
