async function loadPortalState() {
  const response = await fetch("./portal_state.json");
  if (!response.ok) {
    throw new Error("Failed to load portal_state.json");
  }
  return response.json();
}

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
};

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

function updateRunnerFormForPipeline() {
  const selected = document.getElementById("runner-pipeline").selectedOptions[0];
  if (!selected) {
    return;
  }
  const required = new Set((selected.dataset.requiredInputs || "").split(",").filter(Boolean));
  const acceptsPdf = selected.dataset.acceptsPdf === "true";
  const pipelineId = selected.value;
  const visibility = {
    jira_issue_key: required.has("jira_issue_key"),
    confluence_page_id: required.has("confluence_page_id"),
    pdf: acceptsPdf,
    publish_wiki: pipelineId === "full_real_data_smoke",
    topic: pipelineId === "full_real_data_smoke",
    mock_response: pipelineId === "full_real_data_smoke",
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
    request.textContent = [run.request?.jira_issue_key, run.request?.confluence_page_id].filter(Boolean).join(" / ");
    button.append(title, document.createElement("br"), status, document.createElement("br"), request);
    button.addEventListener("click", () => {
      runnerState.selectedRunId = run.run_id;
      loadRunnerDetail(run.run_id);
    });
    target.appendChild(button);
  });
}

function renderRunnerDetail(manifest) {
  const target = document.getElementById("runner-detail");
  target.innerHTML = "";
  const heading = document.createElement("div");
  const statusClass = manifest.status === "failed" ? "runner-status failed" : "runner-status";
  heading.innerHTML = `
    <p><strong>${manifest.label}</strong></p>
    <p><span class="${statusClass}">${manifest.status}</span></p>
    <p><code>${manifest.run_id}</code></p>
  `;
  target.appendChild(heading);

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
}

async function loadRunnerDetail(runId) {
  const manifest = await runnerFetch(`/api/runs/${runId}`);
  renderRunnerDetail(manifest);
}

async function refreshRunnerRuns() {
  const payload = await runnerFetch("/api/runs");
  renderRunnerRuns(payload);
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
  renderPipelineOptions(pipelines);
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
  const tokenInput = document.getElementById("runner-token");
  tokenInput.value = runnerState.token;
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

  document.getElementById("runner-run-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData();
    form.append("pipeline_id", document.getElementById("runner-pipeline").value);
    form.append("jira_issue_key", document.getElementById("runner-jira-issue").value);
    form.append("confluence_page_id", document.getElementById("runner-confluence-page").value);
    form.append("preferred_parser", document.getElementById("runner-parser").value);
    form.append("publish_wiki", document.getElementById("runner-publish-wiki").checked ? "true" : "false");
    form.append("topic_slug", document.getElementById("runner-topic-slug").value);
    form.append("topic_title", document.getElementById("runner-topic-title").value);
    form.append("mock_response", document.getElementById("runner-mock-response").value);
    const file = document.getElementById("runner-pdf").files[0];
    if (file) {
      form.append("pdf", file);
    }
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

function renderTaskWorkbench(workbench) {
  let selectedTaskId = workbench.selected_task_id;
  const taskDetailsById = workbench.task_details_by_id || {};
  const entry = workbench.new_task_entry;
  document.getElementById("new-task-entry").textContent =
    `${entry.default_task_type}: ${entry.input_hint}`;

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

async function bootPortal() {
  const state = await loadPortalState();
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

bootPortal().catch((error) => {
  document.body.innerHTML = `<pre>${error.message}</pre>`;
});
