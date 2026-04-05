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

async function bootPortal() {
  const state = await loadPortalState();
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

