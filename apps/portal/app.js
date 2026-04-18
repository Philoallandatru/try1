async function loadPortalState() {
  const response = await fetch("./portal_state.json");
  if (!response.ok) {
    throw new Error("Failed to load portal_state.json");
  }
  return response.json();
}

let currentPortalState = null;

function renderList(target, entries, formatter) {
  target.innerHTML = "";
  entries.forEach((entry) => {
    const li = document.createElement("li");
    li.textContent = formatter(entry);
    target.appendChild(li);
  });
}

function renderInventory(target, rows) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.title}</td>
      <td>${row.source_type}</td>
      <td>${row.authority_level}</td>
      <td>${row.version}</td>
      <td>${row.language}</td>
    `;
    target.appendChild(tr);
  });
}

function renderSearchResults(target, rows, inspectionTarget) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const card = document.createElement("button");
    card.className = "search-card";
    card.type = "button";
    card.innerHTML = `
      <strong>${row.title}</strong>
      <span>${row.authority_level}</span>
      <span>score: ${row.scores.total}</span>
      <span>citation: ${row.citation.document} / v${row.citation.version} / p${row.citation.page ?? "-"}</span>
    `;
    card.addEventListener("click", () => {
      inspectionTarget.textContent = JSON.stringify(row.inspection, null, 2);
    });
    target.appendChild(card);
  });
}

function renderBadgeGrid(target, rows, className) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = className;
    const label = document.createElement("strong");
    label.textContent = row.label;
    const status = document.createElement("span");
    status.textContent = row.status;
    item.append(label, status);
    if (row.preview) {
      const preview = document.createElement("small");
      preview.textContent = row.preview;
      item.append(preview);
    }
    target.appendChild(item);
  });
}

function renderEventList(target, rows) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "event-row";
    item.innerHTML = `
      <strong>${row.action}</strong>
      <span>${row.created_at}</span>
      <span>${row.requested_by}</span>
      <code>${row.summary}</code>
    `;
    target.appendChild(item);
  });
}

function renderArtifactInventory(target, rows) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "artifact-row";
    item.innerHTML = `
      <strong>${row.artifact_type}</strong>
      <span>${row.status}</span>
      <span>stale: ${row.stale}</span>
      <code>${row.path}</code>
    `;
    target.appendChild(item);
  });
}

function renderCommandRecipes(target, rows) {
  target.innerHTML = "";
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "command-row";
    item.innerHTML = `
      <strong>${row.label}</strong>
      <code>${row.command}</code>
    `;
    target.appendChild(item);
  });
}

const runnerState = {
  token: localStorage.getItem("portalRunnerToken") || "",
  selectedRunId: null,
  pollTimer: null,
  wired: false,
};

const RUNNER_TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

function runnerHeaders() {
  return runnerState.token ? { Authorization: `Bearer ${runnerState.token}` } : {};
}

async function runnerFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...runnerHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {
      // Keep the status text when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

function setRunnerStatus(message, failed = false) {
  const target = document.getElementById("runner-status");
  target.textContent = message;
  target.className = failed ? "failed" : "";
}

function renderRunnerEvents(target, rows) {
  target.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.textContent = "No runner events recorded yet.";
    target.appendChild(empty);
    return;
  }
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "runner-event-row";
    item.innerHTML = `
      <strong>${row.event}</strong>
      <span>${row.created_at || "-"}</span>
      <code>${JSON.stringify(row).slice(0, 240)}</code>
    `;
    target.appendChild(item);
  });
}

function renderPipelineOptions(payload) {
  const select = document.getElementById("runner-pipeline");
  select.innerHTML = "";
  payload.pipelines
    .filter((pipeline) => pipeline.enabled)
    .forEach((pipeline) => {
      const option = document.createElement("option");
      option.value = pipeline.pipeline_id;
      option.textContent = pipeline.label;
      option.dataset.acceptsPdf = String(pipeline.accepts_pdf);
      option.dataset.requiredInputs = pipeline.required_inputs.join(",");
      select.appendChild(option);
    });
  updateRunnerFormForPipeline();
}

function renderSpecAssetOptions(payload) {
  const select = document.getElementById("runner-spec-asset");
  const saved = JSON.parse(localStorage.getItem("portalRunnerForm") || "{}");
  const current = select.value || saved.specAsset || "";
  select.innerHTML = "";
  const upload = document.createElement("option");
  upload.value = "";
  upload.textContent = "Upload PDF for this run";
  select.appendChild(upload);
  (payload.assets || []).forEach((asset) => {
    const option = document.createElement("option");
    option.value = asset.asset_id;
    option.textContent = `${asset.display_name || asset.asset_id} / ${asset.version} / ${asset.parser_used || "parser"}`;
    select.appendChild(option);
  });
  select.value = current;
}

function updateRunnerFormForPipeline() {
  const selected = document.getElementById("runner-pipeline").selectedOptions[0];
  if (!selected) {
    return;
  }
  const required = new Set((selected.dataset.requiredInputs || "").split(",").filter(Boolean));
  const acceptsPdf = selected.dataset.acceptsPdf === "true";
  const pipelineId = selected.value;
  const isProfilePromptDebug = pipelineId === "profile_prompt_debug";
  const visibility = {
    jira_issue_key: required.has("jira_issue_key") || isProfilePromptDebug,
    confluence_selector: required.has("confluence_selector") || required.has("confluence_page_id") || isProfilePromptDebug,
    confluence_page_id: required.has("confluence_page_id") || ((required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "page"),
    confluence_page_ids: (required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "pages",
    confluence_root_page_id: (required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "page_tree",
    confluence_max_depth: (required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "page_tree",
    confluence_space_key: (required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "space_slice",
    confluence_label: (required.has("confluence_selector") || isProfilePromptDebug) && document.getElementById("runner-confluence-scope").value === "space_slice",
    pdf: acceptsPdf,
    spec_asset: pipelineId === "jira_pdf_qa_smoke" || isProfilePromptDebug,
    spec_asset_id: pipelineId === "pdf_ingest_smoke" || (acceptsPdf && document.getElementById("runner-spec-asset").value === ""),
    publish_wiki: pipelineId === "full_real_data_smoke",
    topic: pipelineId === "full_real_data_smoke",
    mock_response: pipelineId === "full_real_data_smoke" || isProfilePromptDebug,
    profile: isProfilePromptDebug,
    prompt: isProfilePromptDebug,
  };
  document.querySelectorAll("[data-runner-field]").forEach((field) => {
    const name = field.dataset.runnerField;
    field.hidden = visibility[name] === false;
  });
}

function renderRunnerRuns(payload) {
  const target = document.getElementById("runner-runs");
  target.innerHTML = "";
  payload.runs.forEach((run) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `runner-run-card${run.run_id === runnerState.selectedRunId ? " selected" : ""}`;
    const title = document.createElement("strong");
    title.textContent = run.label;
    const status = document.createElement("span");
    status.textContent = `${run.status} / ${run.run_id}`;
    const request = document.createElement("small");
    request.textContent = [run.request?.jira_issue_key, run.request?.confluence_page_id, run.request?.profile].filter(Boolean).join(" / ");
    button.append(title, document.createElement("br"), status, document.createElement("br"), request);
    button.addEventListener("click", () => {
      runnerState.selectedRunId = run.run_id;
      loadRunnerDetail(run.run_id);
    });
    target.appendChild(button);
  });
}

function renderRunnerDetail(manifest, events) {
  const target = document.getElementById("runner-detail");
  const actions = document.getElementById("runner-run-actions");
  const eventTarget = document.getElementById("runner-events");
  target.innerHTML = "";
  actions.innerHTML = "";
  const heading = document.createElement("div");
  const statusClass = manifest.status === "failed" ? "runner-status failed" : "runner-status";
  heading.innerHTML = `
    <p><strong>${manifest.label}</strong></p>
    <p><span class="${statusClass}">${manifest.status}</span></p>
    <p><code>${manifest.run_id}</code></p>
  `;
  target.appendChild(heading);
  if (!RUNNER_TERMINAL_STATUSES.has(manifest.status)) {
    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.id = "runner-cancel";
    cancelButton.className = "runner-secondary-action";
    cancelButton.textContent = "Cancel Run";
    cancelButton.addEventListener("click", async () => {
      try {
        await runnerFetch(`/api/runs/${manifest.run_id}/cancel`, { method: "POST" });
        setRunnerStatus(`Cancel requested for ${manifest.run_id}`);
        await refreshRunnerRuns();
      } catch (error) {
        setRunnerStatus(error.message, true);
      }
    });
    actions.appendChild(cancelButton);
  }

  (manifest.steps || []).forEach((step) => {
    const card = document.createElement("div");
    card.className = "runner-step-card";
    const title = document.createElement("strong");
    title.textContent = step.label;
    const status = document.createElement("span");
    status.className = step.status === "failed" ? "runner-status failed" : "runner-status";
    status.textContent = step.status;
    const duration = document.createElement("p");
    duration.textContent = `${step.duration_seconds ?? "-"} seconds`;
    const logs = document.createElement("pre");
    logs.textContent = (step.latest_logs || []).join("\n");
    card.append(title, document.createTextNode(" "), status, duration);
    if (step.error) {
      const error = document.createElement("p");
      error.textContent = step.error;
      card.appendChild(error);
    }
    card.appendChild(logs);
    target.appendChild(card);
  });

  const artifacts = manifest.artifacts || {};
  if (Object.keys(artifacts).length > 0) {
    const list = document.createElement("div");
    list.className = "runner-step-card";
    const title = document.createElement("strong");
    title.textContent = "Artifacts";
    list.appendChild(title);
    Object.keys(artifacts).forEach((name) => {
      const row = document.createElement("p");
      const link = document.createElement("a");
      link.href = `/api/runs/${manifest.run_id}/artifacts/${name}`;
      link.textContent = name;
      link.target = "_blank";
      row.appendChild(link);
      list.appendChild(row);
    });
    target.appendChild(list);
  }
  renderRunnerEvents(eventTarget, events || []);
}

async function loadRunnerDetail(runId) {
  const [manifest, eventPayload] = await Promise.all([
    runnerFetch(`/api/runs/${runId}`),
    runnerFetch(`/api/runs/${runId}/events`),
  ]);
  renderRunnerDetail(manifest, eventPayload.events || []);
}

async function refreshRunnerRuns() {
  const payload = await runnerFetch("/api/runs");
  renderRunnerRuns(payload);
  const assets = await runnerFetch("/api/spec-assets");
  renderSpecAssetOptions(assets);
  if (!runnerState.selectedRunId && payload.runs.length > 0) {
    runnerState.selectedRunId = payload.runs[0].run_id;
  }
  if (runnerState.selectedRunId) {
    await loadRunnerDetail(runnerState.selectedRunId);
  }
}

async function connectRunner() {
  await runnerFetch("/api/auth/check", { method: "POST" });
  const pipelines = await runnerFetch("/api/pipelines");
  const assets = await runnerFetch("/api/spec-assets");
  renderPipelineOptions(pipelines);
  renderSpecAssetOptions(assets);
  document.getElementById("runner-run-form").hidden = false;
  setRunnerStatus("Connected to portal runner.");
  await refreshRunnerRuns();
  if (!runnerState.pollTimer) {
    runnerState.pollTimer = setInterval(() => {
      refreshRunnerRuns().catch((error) => setRunnerStatus(error.message, true));
    }, 3000);
  }
}

function wireRunnerPanel() {
  if (runnerState.wired) {
    return;
  }
  runnerState.wired = true;
  const tokenInput = document.getElementById("runner-token");
  tokenInput.value = runnerState.token;
  restoreRunnerForm();
  document.getElementById("runner-auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    runnerState.token = tokenInput.value.trim();
    localStorage.setItem("portalRunnerToken", runnerState.token);
    try {
      await connectRunner();
    } catch (error) {
      setRunnerStatus(error.message, true);
    }
  });

  document.getElementById("runner-pipeline").addEventListener("change", updateRunnerFormForPipeline);
  document.getElementById("runner-confluence-scope").addEventListener("change", updateRunnerFormForPipeline);
  document.getElementById("runner-spec-asset").addEventListener("change", updateRunnerFormForPipeline);

  document.getElementById("runner-run-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData();
    form.append("pipeline_id", document.getElementById("runner-pipeline").value);
    form.append("jira_issue_key", document.getElementById("runner-jira-issue").value);
    form.append("confluence_page_id", document.getElementById("runner-confluence-page").value);
    form.append("confluence_scope", document.getElementById("runner-confluence-scope").value);
    form.append("confluence_page_ids", document.getElementById("runner-confluence-pages").value);
    form.append("confluence_root_page_id", document.getElementById("runner-confluence-root").value);
    form.append("confluence_space_key", document.getElementById("runner-confluence-space").value);
    form.append("confluence_label", document.getElementById("runner-confluence-label").value);
    form.append("confluence_max_depth", document.getElementById("runner-confluence-depth").value);
    form.append("spec_asset_id", document.getElementById("runner-spec-asset").value || document.getElementById("runner-spec-asset-id").value);
    form.append("preferred_parser", document.getElementById("runner-parser").value);
    form.append("publish_wiki", document.getElementById("runner-publish-wiki").checked ? "true" : "false");
    form.append("topic_slug", document.getElementById("runner-topic-slug").value);
    form.append("topic_title", document.getElementById("runner-topic-title").value);
    form.append("mock_response", document.getElementById("runner-mock-response").value);
    form.append("profile", document.getElementById("runner-profile").value);
    form.append("prompt", document.getElementById("runner-prompt").value);
    const file = document.getElementById("runner-pdf").files[0];
    if (file) {
      form.append("pdf", file);
    }
    saveRunnerForm();
    try {
      const manifest = await runnerFetch("/api/runs", { method: "POST", body: form });
      runnerState.selectedRunId = manifest.run_id;
      setRunnerStatus(`Started ${manifest.run_id}`);
      await refreshRunnerRuns();
    } catch (error) {
      setRunnerStatus(error.message, true);
    }
  });

  if (runnerState.token) {
    connectRunner().catch(() => setRunnerStatus("Enter the runner token to connect."));
  } else {
    setRunnerStatus("Start apps.portal_runner.server and enter the shared runner token.");
  }
}

function saveRunnerForm() {
  const values = {
    pipeline: document.getElementById("runner-pipeline").value,
    jiraIssue: document.getElementById("runner-jira-issue").value,
    confluencePage: document.getElementById("runner-confluence-page").value,
    confluenceScope: document.getElementById("runner-confluence-scope").value,
    confluencePages: document.getElementById("runner-confluence-pages").value,
    confluenceRoot: document.getElementById("runner-confluence-root").value,
    confluenceDepth: document.getElementById("runner-confluence-depth").value,
    confluenceSpace: document.getElementById("runner-confluence-space").value,
    confluenceLabel: document.getElementById("runner-confluence-label").value,
    specAsset: document.getElementById("runner-spec-asset").value,
    specAssetId: document.getElementById("runner-spec-asset-id").value,
    parser: document.getElementById("runner-parser").value,
    topicSlug: document.getElementById("runner-topic-slug").value,
    topicTitle: document.getElementById("runner-topic-title").value,
    mockResponse: document.getElementById("runner-mock-response").value,
    profile: document.getElementById("runner-profile").value,
    prompt: document.getElementById("runner-prompt").value,
    publishWiki: document.getElementById("runner-publish-wiki").checked,
  };
  localStorage.setItem("portalRunnerForm", JSON.stringify(values));
}

function restoreRunnerForm() {
  const raw = localStorage.getItem("portalRunnerForm");
  if (!raw) {
    return;
  }
  const values = JSON.parse(raw);
  const assign = (id, value) => {
    if (value !== undefined && document.getElementById(id)) {
      document.getElementById(id).value = value;
    }
  };
  assign("runner-jira-issue", values.jiraIssue);
  assign("runner-confluence-page", values.confluencePage);
  assign("runner-confluence-scope", values.confluenceScope);
  assign("runner-confluence-pages", values.confluencePages);
  assign("runner-confluence-root", values.confluenceRoot);
  assign("runner-confluence-depth", values.confluenceDepth);
  assign("runner-confluence-space", values.confluenceSpace);
  assign("runner-confluence-label", values.confluenceLabel);
  assign("runner-spec-asset-id", values.specAssetId);
  assign("runner-parser", values.parser);
  assign("runner-topic-slug", values.topicSlug);
  assign("runner-topic-title", values.topicTitle);
  assign("runner-mock-response", values.mockResponse);
  assign("runner-profile", values.profile);
  assign("runner-prompt", values.prompt);
  document.getElementById("runner-publish-wiki").checked = values.publishWiki !== false;
}

function renderTaskWorkbench(workbench) {
  let selectedTaskId = workbench.selected_task_id;
  const taskDetailsById = workbench.task_details_by_id || {};
  const entry = workbench.new_task_entry;
  document.getElementById("new-task-entry").textContent =
    `${entry.default_task_type}: ${entry.input_hint}`;
  const issueInput = document.getElementById("new-task-issue-key");
  const profileSelect = document.getElementById("new-task-profile");
  const commandPreview = document.getElementById("new-task-command-preview");
  const runButton = document.getElementById("new-task-run");
  const issueField = (entry.fields || []).find((field) => field.id === "issue_key");
  const profileField = (entry.fields || []).find((field) => field.id === "profile");
  issueInput.value = issueField?.value || "";
  profileSelect.innerHTML = "";
  (entry.available_profiles || []).forEach((profile) => {
    const option = document.createElement("option");
    option.value = profile;
    option.textContent = profile;
    profileSelect.appendChild(option);
  });
  if (profileField?.value) {
    profileSelect.value = profileField.value;
  }
  function renderNewTaskCommandPreview() {
    const issueKey = issueInput.value.trim() || "<issue-key>";
    const profile = profileSelect.value || "<profile>";
    commandPreview.textContent = (entry.command_preview || "").replace(
      /--profile\s+\S+\s+--issue-key\s+\S+/,
      `--profile ${profile} --issue-key ${issueKey}`
    );
  }
  issueInput.oninput = renderNewTaskCommandPreview;
  profileSelect.onchange = renderNewTaskCommandPreview;
  runButton.onclick = async () => {
    renderNewTaskCommandPreview();
    if (!currentPortalState?.workspace_dir) {
      setRunnerStatus("Portal state has no workspace_dir; cannot run analysis from the page.", true);
      return;
    }
    if (!runnerState.token) {
      setRunnerStatus("Connect the runner before starting an analysis from the page.", true);
      return;
    }
    try {
      setRunnerStatus(`Running analyze-jira for ${issueInput.value.trim() || "<issue-key>"}...`);
      const payload = await runnerFetch("/api/workspace/analyze-jira", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_dir: currentPortalState.workspace_dir,
          profile: profileSelect.value,
          issue_key: issueInput.value.trim(),
        }),
      });
      currentPortalState = payload.portal_state;
      renderPortal(payload.portal_state);
      setRunnerStatus(`Analysis completed for ${issueInput.value.trim()}.`);
    } catch (error) {
      setRunnerStatus(error.message, true);
    }
  };
  renderNewTaskCommandPreview();

  document.getElementById("task-filters").textContent =
    `Filters: ${workbench.filters.status.join(", ")} / owner ${workbench.filters.owner.join(", ")} / project ${workbench.filters.project.join(", ")}`;

  const taskList = document.getElementById("task-list");
  const controls = document.getElementById("task-controls");
  const detailTabs = document.getElementById("task-detail-tabs");
  const reportTabs = document.getElementById("report-tabs");
  const knowledgePanels = document.getElementById("knowledge-panels");
  const controlEvents = document.getElementById("control-events");
  const artifactInventory = document.getElementById("artifact-inventory");
  const commandRecipes = document.getElementById("command-recipes");
  const retrievalComparison = document.getElementById("retrieval-comparison");

  function renderSelectedTask() {
    taskList.innerHTML = "";
    workbench.tasks.forEach((task) => {
      const button = document.createElement("button");
      button.className = `task-card${task.task_id === selectedTaskId ? " selected" : ""}`;
      button.type = "button";
      const issue = document.createElement("strong");
      issue.textContent = task.issue_key;
      const meta = document.createElement("span");
      meta.textContent = `${task.status} / ${task.owner}`;
      const summary = document.createElement("span");
      summary.textContent = task.summary;
      button.append(issue, meta, summary);
      button.addEventListener("click", () => {
        selectedTaskId = task.task_id;
        renderSelectedTask();
      });
      taskList.appendChild(button);
    });

    const selectedDetails = taskDetailsById[selectedTaskId] || {
      detail_tabs: workbench.detail_tabs,
      report_tabs: workbench.report_tabs,
      knowledge_panels: workbench.knowledge_panels,
      control_events: workbench.control_events || [],
      artifact_inventory: workbench.artifact_inventory || [],
      command_recipes: workbench.command_recipes || [],
      retrieval_comparison: workbench.retrieval_comparison,
      controls: workbench.controls,
    };

    controls.innerHTML = "";
    selectedDetails.controls.forEach((control) => {
      const button = document.createElement("button");
      button.className = "task-control";
      button.type = "button";
      button.textContent = control;
      controls.appendChild(button);
    });

    detailTabs.innerHTML = "";
    selectedDetails.detail_tabs.forEach((tab) => {
      const section = document.createElement("section");
      section.className = "detail-tab";
      const heading = document.createElement("h3");
      heading.textContent = tab.label;
      const body = document.createElement("p");
      body.textContent = tab.content;
      section.append(heading, body);
      detailTabs.appendChild(section);
    });

    renderBadgeGrid(reportTabs, selectedDetails.report_tabs, "status-pill");
    renderBadgeGrid(knowledgePanels, selectedDetails.knowledge_panels, "status-pill");
    renderEventList(controlEvents, selectedDetails.control_events || []);
    renderArtifactInventory(artifactInventory, selectedDetails.artifact_inventory || []);
    renderCommandRecipes(commandRecipes, selectedDetails.command_recipes || []);
    retrievalComparison.textContent = JSON.stringify(selectedDetails.retrieval_comparison, null, 2);
  }

  renderSelectedTask();
}

function renderPortal(state) {
  wireRunnerPanel();
  renderTaskWorkbench(state.task_workbench);
  renderList(
    document.getElementById("ingestion-status-list"),
    state.ingestion_status,
    (item) => `${item.source_type}: ${item.status} (${item.document_count} docs)`
  );
  renderList(
    document.getElementById("evaluation-health-list"),
    Object.entries(state.evaluation_health).map(([metric, value]) => ({ metric, value })),
    (item) => `${item.metric}: ${item.value}`
  );
  renderInventory(
    document.querySelector("#corpus-inventory-table tbody"),
    state.corpus_inventory
  );
  document.getElementById("search-query").textContent = `Seed query: ${state.search_query}`;
  const inspectionTarget = document.getElementById("citation-inspection");
  inspectionTarget.textContent = JSON.stringify(state.citation_inspection, null, 2);
  renderSearchResults(
    document.getElementById("search-results"),
    state.search_workspace,
    inspectionTarget
  );
}

async function bootPortal() {
  currentPortalState = await loadPortalState();
  renderPortal(currentPortalState);
}

bootPortal().catch((error) => {
  document.body.innerHTML = `<pre>${error.message}</pre>`;
});
