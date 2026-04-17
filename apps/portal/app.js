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
    retrievalComparison.textContent = JSON.stringify(selectedDetails.retrieval_comparison, null, 2);
  }

  renderSelectedTask();
}

async function bootPortal() {
  const state = await loadPortalState();
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
