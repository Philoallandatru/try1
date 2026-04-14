# Topic-Routed VitePress Wiki Evidence

## Scope

- Workspace curated wiki control plane
- Topic-routed compilation
- VitePress-ready site generation
- Real local VitePress build verification
- UI/UX refinements for topic, summary, and analysis pages

## Commands Run

```powershell
python -m unittest tests.ops.test_workspace_cli tests.ops.test_wiki_site_builder -v
python -m compileall services\workspace services\wiki_site scripts\workspace_cli.py tests\ops\test_workspace_cli.py tests\ops\test_wiki_site_builder.py
python scripts/workspace_cli.py publish-wiki .tmp\workspace-run --manifest .tmp\workspace-run\route-manifest.json --renderer vitepress --verify-site-build --llm-backend mock --llm-mock-response "Mock published content"
```

## Observed Results

- Unit/integration tests passed for:
  - workspace control plane
  - topic-routed compilation
  - VitePress-ready output generation
  - publish flow with optional site-build verification
- Python compile checks passed for updated workspace and wiki-site modules.
- `publish-wiki` succeeded with:
  - `summary_count = 1`
  - `analysis_count = 1`
  - `topic_page_count = 1`
- Real site verification succeeded with:
  - `renderer = vitepress`
  - `ok = true`
  - `dist_exists = true`

## Output Artifacts

- `.tmp/workspace-run/wiki/topics.json`
- `.tmp/workspace-run/wiki/routes.json`
- `.tmp/workspace-run/wiki/compilation-manifest.json`
- `.tmp/workspace-run/wiki/reports/compilation-report.json`
- `.tmp/workspace-run/wiki/reports/vitepress-build-report.json`
- `.tmp/workspace-run/wiki/vitepress_site/`

## Notes

- Windows-specific issues were handled in the implementation:
  - UTF-8 BOM route-manifest parsing
  - `npm` / `npm.cmd` executable resolution
  - UTF-8-safe subprocess output decoding
  - VitePress temp/dist cleanup before verification
- Current UX improvements are presentation-layer only and do not weaken canonical document, PageIndex, ACL, or citation contracts.
