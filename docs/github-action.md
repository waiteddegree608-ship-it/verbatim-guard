# Check quotations in a pull request

Use Verbatim Guard as a reusable GitHub Action when your repository already contains an evidence bundle. The action reads your supplied text and quotations; it does not extract evidence from PDFs or connect to a model.

```yaml
name: Evidence checks
on: [push, pull_request]
permissions:
  contents: read
jobs:
  evidence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: waiteddegree608-ship-it/verbatim-guard@v0.2.0
        id: evidence
        with:
          bundle: evidence.json
          mode: exact
```

Copy [examples/passing.json](../examples/passing.json) into your repository as `evidence.json` to try it. Replace the synthetic sources and claims with your actual evidence. Save the workflow as `.github/workflows/evidence.yml`.

Requires Python 3.10+ on PATH and a Bash shell. CI exercises the action on GitHub-hosted Ubuntu and Windows runners. The validator itself makes no network calls and installs no dependencies; GitHub still downloads the action and any setup actions used by your workflow. Checkout and Python setup are explicit steps you control. For reproducible use, you can replace the version tag with the release's full commit SHA.

## Inputs and outputs

| Input | Default | Meaning |
| --- | --- | --- |
| `bundle` | Required | UTF-8 JSON file path, relative to the workflow working directory or absolute. Stdin is not supported. |
| `mode` | `exact` | `exact` or `whitespace`; folding is opt-in. |

| Output | Meaning |
| --- | --- |
| `input-valid` | String `true` if the bundle was read and validated; otherwise `false`. |
| `ok` | String `true` only if all checks passed. |
| `passed`, `failed`, `total` | Decimal counts; all zero for invalid input. |

Failed evidence returns exit code 1, and invalid input returns 2. Both fail the step and normally the job. To collect outputs without stopping a custom workflow, use `continue-on-error: true` on the action step and check `steps.evidence.outcome`; this deliberately makes the check non-blocking unless you add a later failure gate.

## What appears in GitHub

- Failed checks produce error annotations containing status, claim ID, source ID, and the reason. At most 50 annotations are emitted; totals still include all failures.
- The job summary shows pass/total counts and a status breakdown.
- Source text and quotations are not copied into annotations or summaries. IDs and input errors appear in logs, so keep secrets out of those fields.
- Source IDs are labels inside the JSON bundle. They are not interpreted as repository file paths, and annotations do not pretend to point at source-file line numbers.

Input text is passed through environment variables rather than interpolated into shell code. The runner uses isolated Python, imports this action's bundled validator, and escapes workflow commands. It needs no GitHub token or write permissions.

The bundle limit is 8 MiB, with up to 100 sources and 1,000 claims. These limits reduce accidental overload; they do not constitute a CPU or memory budget. For untrusted inputs, also set a workflow `timeout-minutes` appropriate to your repository.

For JSON or HTML artifacts, use the [CLI](../README.md#json-input-and-ci). This action only produces annotations, summaries, and scalar outputs; it does not upload your evidence.

GitHub's [workflow-command reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands) describes annotations, outputs, and job summaries.
