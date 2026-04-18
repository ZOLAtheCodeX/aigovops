# framework-monitor-state.json

Runtime state file for the `framework-monitor` GitHub Actions workflow defined in `.github/workflows/framework-monitor.yml`.

## Schema

```json
{
  "<source-id>": {
    "digest": "<sha256 of the last fetched response body>",
    "last_probed_url": "<URL that was probed>"
  }
}
```

`source-id` values are declared in the workflow's `SOURCES` list. Current IDs: `nist-ai-rmf`, `nist-ai-rmf-playbook`, `nist-ai-600-1-genai-profile`, `iso-42001`, `eu-ai-act-eur-lex`, `eu-ai-act-commission-policy`, `eu-ai-office-codes-of-practice`, `cen-cenelec-jtc21`.

## Initialization

The file is seeded empty (`{}`) so the first scheduled run records baseline digests without opening change-detected issues. The workflow itself auto-commits updates on subsequent runs via the `framework-monitor` bot identity.

## Do not hand-edit in a feature branch

This file is bot-owned. Merging a hand-edited copy will cause the next run to report spurious changes against whichever sources drifted between your edit and the next probe.

## Manual reset procedure

If the file becomes corrupt or falsely triggers issues, reset to `{}` on `main` with a commit message like `chore(framework-monitor): reset digest state`. The next run re-baselines.
