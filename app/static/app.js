const state = {
  categories: [],
  sources: [],
  mappings: [],
  settings: {
    duration_target_minutes: 10,
    max_item_age_hours: 48,
    schedule_cron: "0 8 * * 1,3,5",
    timezone: "Europe/Paris",
  },
  budgetStatus: null,
  jobs: [],
};

const statusNode = document.getElementById("status");

function setStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.className = isError ? "error" : "ok";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

function renderCategories() {
  const list = document.getElementById("category-list");
  list.innerHTML = "";

  state.categories.forEach((category) => {
    const item = document.createElement("li");
    item.className = "item";
    item.innerHTML = `
      <div>
        <strong>${category.name}</strong> (poids ${category.default_weight})
        <div>${category.description || ""}</div>
        <small>${category.enabled ? "Active" : "Inactive"}</small>
      </div>
      <div class="actions">
        <button data-action="toggle" data-id="${category.id}">${category.enabled ? "Desactiver" : "Activer"}</button>
        <button data-action="delete" data-id="${category.id}">Supprimer</button>
      </div>
    `;
    list.appendChild(item);
  });

  const categorySelect = document.getElementById("mapping-category");
  categorySelect.innerHTML = "";
  state.categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    categorySelect.appendChild(option);
  });
}

function renderSources() {
  const list = document.getElementById("source-list");
  list.innerHTML = "";

  state.sources.forEach((source) => {
    const item = document.createElement("li");
    item.className = "item";
    item.innerHTML = `
      <div>
        <strong>${source.title}</strong>
        <div>${source.url}</div>
        <small>${source.enabled ? "Actif" : "Inactif"} - Sante: ${source.health_status}${source.health_message ? ` (${source.health_message})` : ""}</small>
      </div>
      <div class="actions">
        <button data-action="health" data-id="${source.id}">Tester</button>
        <button data-action="toggle" data-id="${source.id}">${source.enabled ? "Desactiver" : "Activer"}</button>
        <button data-action="delete" data-id="${source.id}">Supprimer</button>
      </div>
    `;
    list.appendChild(item);
  });

  const sourceSelect = document.getElementById("mapping-source");
  sourceSelect.innerHTML = "";
  state.sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source.id;
    option.textContent = source.title;
    sourceSelect.appendChild(option);
  });
}

function renderMappings() {
  const list = document.getElementById("mapping-list");
  list.innerHTML = "";

  state.mappings.forEach((mapping) => {
    const item = document.createElement("li");
    item.className = "item";
    item.innerHTML = `
      <div>
        <strong>${mapping.category_name}</strong> -> ${mapping.source_title}
        <div>${mapping.source_url}</div>
      </div>
      <div class="actions">
        <button data-action="delete" data-category-id="${mapping.category_id}" data-source-id="${mapping.source_id}">Retirer</button>
      </div>
    `;
    list.appendChild(item);
  });
}

async function reloadAll() {
  const [categories, sources, mappings, settings, schedule] = await Promise.all([
    api("/api/categories"),
    api("/api/rss-sources"),
    api("/api/mappings"),
    api("/api/settings/duration-target"),
    api("/api/settings/schedule"),
  ]);
  state.categories = categories;
  state.sources = sources;
  state.mappings = mappings;
  state.settings = {
    ...state.settings,
    ...settings,
    ...schedule,
  };
  renderCategories();
  renderSources();
  renderMappings();
  document.getElementById("duration-target").value = state.settings.duration_target_minutes;
  document.getElementById("schedule-cron").value = state.settings.schedule_cron;
  document.getElementById("schedule-timezone").value = state.settings.timezone;
  renderScheduleSummary(state.settings);
  await reloadOps();
}

function renderPreview(preview) {
  const output = document.getElementById("preview-output");
  output.textContent = JSON.stringify(preview, null, 2);
}

function renderScheduleSummary(schedule) {
  const summary = document.getElementById("schedule-summary");
  const nextRuns = (schedule.next_runs || []).slice(0, 3).join("\n");
  summary.textContent = `Episodes/semaine (estimation): ${schedule.episodes_per_week_hint ?? "n/a"}\nProchains runs:\n${nextRuns || "aucun"}`;
}

function renderOps() {
  const budgetOutput = document.getElementById("budget-output");
  const jobsOutput = document.getElementById("jobs-output");

  budgetOutput.textContent = JSON.stringify(state.budgetStatus || { message: "Budget indisponible" }, null, 2);
  jobsOutput.textContent = JSON.stringify(state.jobs || [], null, 2);
}

async function reloadOps() {
  const [budgetStatus, jobs] = await Promise.all([api("/api/budget-status"), api("/api/jobs")]);
  state.budgetStatus = budgetStatus;
  state.jobs = jobs;
  renderOps();
}

document.getElementById("category-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/categories", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("category-name").value,
        description: document.getElementById("category-description").value,
        default_weight: Number(document.getElementById("category-weight").value),
        enabled: document.getElementById("category-enabled").checked,
      }),
    });
    event.target.reset();
    document.getElementById("category-enabled").checked = true;
    document.getElementById("category-weight").value = 1;
    setStatus("Categorie ajoutee");
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("source-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/rss-sources", {
      method: "POST",
      body: JSON.stringify({
        url: document.getElementById("source-url").value,
        title: document.getElementById("source-title").value,
        enabled: document.getElementById("source-enabled").checked,
      }),
    });
    event.target.reset();
    document.getElementById("source-enabled").checked = true;
    setStatus("Flux RSS ajoute");
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("mapping-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/mappings", {
      method: "POST",
      body: JSON.stringify({
        category_id: document.getElementById("mapping-category").value,
        source_id: document.getElementById("mapping-source").value,
      }),
    });
    setStatus("Mapping ajoute");
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("category-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const id = button.dataset.id;
  const action = button.dataset.action;
  const category = state.categories.find((item) => item.id === id);

  try {
    if (action === "toggle" && category) {
      await api(`/api/categories/${id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !Boolean(category.enabled) }),
      });
      setStatus("Categorie mise a jour");
    } else if (action === "delete") {
      await api(`/api/categories/${id}`, { method: "DELETE" });
      setStatus("Categorie supprimee");
    }
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("source-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const id = button.dataset.id;
  const action = button.dataset.action;
  const source = state.sources.find((item) => item.id === id);

  try {
    if (action === "toggle" && source) {
      await api(`/api/rss-sources/${id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !Boolean(source.enabled) }),
      });
      setStatus("Flux mis a jour");
    } else if (action === "delete") {
      await api(`/api/rss-sources/${id}`, { method: "DELETE" });
      setStatus("Flux supprime");
    } else if (action === "health") {
      await api(`/api/rss-sources/${id}/health-check`, { method: "POST" });
      setStatus("Test de flux termine");
    }
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("mapping-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const action = button.dataset.action;
  if (action !== "delete") return;

  const categoryId = button.dataset.categoryId;
  const sourceId = button.dataset.sourceId;
  try {
    await api(`/api/mappings?category_id=${encodeURIComponent(categoryId)}&source_id=${encodeURIComponent(sourceId)}`, {
      method: "DELETE",
    });
    setStatus("Mapping supprime");
    await reloadAll();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("duration-plus").addEventListener("click", () => {
  const input = document.getElementById("duration-target");
  input.value = Number(input.value || state.settings.duration_target_minutes) + 1;
});

document.getElementById("duration-minus").addEventListener("click", () => {
  const input = document.getElementById("duration-target");
  const next = Number(input.value || state.settings.duration_target_minutes) - 1;
  input.value = Math.max(1, next);
});

document.getElementById("duration-save").addEventListener("click", async () => {
  const input = document.getElementById("duration-target");
  try {
    const settings = await api("/api/settings/duration-target", {
      method: "PUT",
      body: JSON.stringify({ duration_target_minutes: Number(input.value) }),
    });
    state.settings = settings;
    setStatus(`Duree cible enregistree (${settings.duration_target_minutes} min)`);
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("preview-run").addEventListener("click", async () => {
  try {
    const categoryIds = state.categories.filter((item) => Boolean(item.enabled)).map((item) => item.id);
    const preview = await api("/api/compose/preview", {
      method: "POST",
      body: JSON.stringify({
        category_ids: categoryIds,
        duration_target_minutes: Number(document.getElementById("duration-target").value),
      }),
    });
    renderPreview(preview);
    setStatus("Previsualisation terminee");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("schedule-save").addEventListener("click", async () => {
  try {
    const schedule = await api("/api/settings/schedule", {
      method: "PUT",
      body: JSON.stringify({
        schedule_cron: document.getElementById("schedule-cron").value,
        timezone: document.getElementById("schedule-timezone").value,
      }),
    });
    state.settings = { ...state.settings, ...schedule };
    renderScheduleSummary(state.settings);
    setStatus("Planification mise a jour");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("schedule-refresh").addEventListener("click", async () => {
  try {
    const schedule = await api("/api/settings/schedule");
    state.settings = { ...state.settings, ...schedule };
    document.getElementById("schedule-cron").value = state.settings.schedule_cron;
    document.getElementById("schedule-timezone").value = state.settings.timezone;
    renderScheduleSummary(state.settings);
    setStatus("Planification rechargee");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("ops-refresh").addEventListener("click", async () => {
  try {
    await reloadOps();
    setStatus("Statuts operations rafraichis");
  } catch (error) {
    setStatus(error.message, true);
  }
});

reloadAll().catch((error) => setStatus(error.message, true));
