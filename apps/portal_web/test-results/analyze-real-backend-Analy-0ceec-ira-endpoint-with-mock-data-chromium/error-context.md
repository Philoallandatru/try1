# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: analyze-real-backend.spec.ts >> Analyze Page - Real Backend Integration >> should test analyze-jira endpoint with mock data
- Location: e2e\analyze-real-backend.spec.ts:243:3

# Error details

```
Error: apiRequestContext.get: connect ECONNREFUSED ::1:8000
Call log:
  - → GET http://localhost:8000/api/workspaces
    - user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.15 Safari/537.36
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - Authorization: Bearer change-me

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: S
      - generic [ref=e7]:
        - paragraph [ref=e8]: SSD Platform
        - heading "SSD Quality Wiki" [level=1] [ref=e9]
    - generic [ref=e10]: Workspace
    - navigation [ref=e11]:
      - link "Analyze" [ref=e12] [cursor=pointer]:
        - /url: /
        - img [ref=e13]
        - text: Analyze
      - link "Search" [ref=e16] [cursor=pointer]:
        - /url: /search
        - img [ref=e17]
        - text: Search
      - link "Runs" [ref=e20] [cursor=pointer]:
        - /url: /runs
        - img [ref=e21]
        - text: Runs
      - link "Analysis" [ref=e24] [cursor=pointer]:
        - /url: /analysis
        - img [ref=e25]
        - text: Analysis
      - link "Daily Report" [ref=e27] [cursor=pointer]:
        - /url: /daily-report
        - img [ref=e28]
        - text: Daily Report
      - link "Batch Analysis" [ref=e30] [cursor=pointer]:
        - /url: /batch-analysis
        - img [ref=e31]
        - text: Batch Analysis
      - link "Documents" [ref=e35] [cursor=pointer]:
        - /url: /documents
        - img [ref=e36]
        - text: Documents
      - link "Sources" [ref=e39] [cursor=pointer]:
        - /url: /sources
        - img [ref=e40]
        - text: Sources
      - link "Profiles" [ref=e44] [cursor=pointer]:
        - /url: /profiles
        - img [ref=e45]
        - text: Profiles
      - link "Wiki" [ref=e48] [cursor=pointer]:
        - /url: /wiki
        - img [ref=e49]
        - text: Wiki
      - link "Reports" [ref=e52] [cursor=pointer]:
        - /url: /reports
        - img [ref=e53]
        - text: Reports
      - link "Spec Lab" [ref=e55] [cursor=pointer]:
        - /url: /spec
        - img [ref=e56]
        - text: Spec Lab
      - link "Admin" [ref=e59] [cursor=pointer]:
        - /url: /admin/
        - img [ref=e60]
        - text: Admin
    - generic [ref=e66]: Runner connected
  - main [ref=e67]:
    - generic [ref=e68]:
      - generic [ref=e71]:
        - paragraph [ref=e72]: Local Runner
        - strong [ref=e73]: Connect Runner
      - generic "Runner controls" [ref=e74]:
        - generic [ref=e75]:
          - text: Token
          - textbox "Token" [ref=e76]:
            - /placeholder: change-me
            - text: change-me
        - generic [ref=e77]:
          - text: Workspace
          - combobox "Workspace" [ref=e78]:
            - option "No workspace" [selected]
        - generic [ref=e79]:
          - text: New
          - generic [ref=e80]:
            - textbox "New Create" [ref=e81]: real-workspace
            - button "Create" [ref=e82] [cursor=pointer]
    - generic [ref=e83]:
      - generic [ref=e84]:
        - generic [ref=e85]:
          - paragraph [ref=e86]: Analyze
          - heading "Deep Jira Analysis" [level=2] [ref=e87]
          - paragraph [ref=e88]: Run deep analysis on Jira issues with cross-source evidence from Confluence and file assets.
        - generic [ref=e89]:
          - generic [ref=e90]:
            - generic [ref=e91]:
              - paragraph [ref=e92]: Setup Checklist
              - strong [ref=e93]: 0 / 4 ready
            - generic [ref=e94]:
              - img [ref=e95]
              - text: Action needed
          - generic [ref=e97]:
            - button "Jira Source Add a Jira source" [ref=e98] [cursor=pointer]:
              - img [ref=e100]
              - strong [ref=e102]: Jira Source
              - generic [ref=e103]: Add a Jira source
            - button "Confluence Source Add a Confluence source" [ref=e104] [cursor=pointer]:
              - img [ref=e106]
              - strong [ref=e108]: Confluence Source
              - generic [ref=e109]: Add a Confluence source
            - button "File Asset Parse or register file assets (specs, policies, etc.)" [ref=e110] [cursor=pointer]:
              - img [ref=e112]
              - strong [ref=e114]: File Asset
              - generic [ref=e115]: Parse or register file assets (specs, policies, etc.)
            - button "Analysis Profile Create a profile with spec and LLM settings" [ref=e116] [cursor=pointer]:
              - img [ref=e118]
              - strong [ref=e120]: Analysis Profile
              - generic [ref=e121]: Create a profile with spec and LLM settings
        - generic [ref=e122]:
          - article [ref=e123]:
            - generic [ref=e124]: system
            - paragraph [ref=e125]: PageIndex-first retrieval, ACL filtering before ranking, citation-bearing answer assembly.
          - article [ref=e126]:
            - generic [ref=e127]: workspace
            - paragraph [ref=e128]: Connect a source and create a profile before starting the next grounded run.
        - button "Advanced" [ref=e129] [cursor=pointer]
        - generic [ref=e130]:
          - generic [ref=e131]:
            - text: Issue Key
            - combobox "Issue Key" [ref=e132]
          - generic [ref=e133]:
            - text: Profile
            - combobox "Profile" [ref=e134]
          - button "Run Analysis" [disabled] [ref=e135]:
            - img [ref=e136]
            - text: Run Analysis
      - generic [ref=e138]:
        - heading "Results" [level=3] [ref=e139]
        - paragraph [ref=e140]: Summary, evidence, citations, and next actions appear after a run.
```