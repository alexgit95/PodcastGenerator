const state = {
  categories: [],
  sources: [],
  mappings: [],
  generationMode: "llm",
  audioMode: "local",
  deterministic: {
    global: null,
    categories: [],
  },
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
const progressBarNode = document.getElementById("generation-progress");
const progressLabelNode = document.getElementById("generation-progress-label");
let tipPopupNode = null;
let activeTipNode = null;

function ensureTipPopup() {
  if (tipPopupNode) {
    return tipPopupNode;
  }
  tipPopupNode = document.createElement("div");
  tipPopupNode.id = "tip-popup";
  tipPopupNode.className = "tip-popup";
  tipPopupNode.hidden = true;
  document.body.appendChild(tipPopupNode);
  return tipPopupNode;
}

function hideTipPopup() {
  const popup = ensureTipPopup();
  popup.hidden = true;
  popup.textContent = "";
  if (activeTipNode) {
    activeTipNode.removeAttribute("data-open");
  }
  activeTipNode = null;
}

function showTipPopup(tipNode) {
  const text = String(tipNode.getAttribute("title") || "").trim();
  if (!text) {
    hideTipPopup();
    return;
  }
  const popup = ensureTipPopup();
  popup.textContent = text;
  popup.hidden = false;

  const rect = tipNode.getBoundingClientRect();
  const popupRect = popup.getBoundingClientRect();
  const scrollX = window.scrollX || window.pageXOffset;
  const scrollY = window.scrollY || window.pageYOffset;
  const left = Math.max(12, Math.min(scrollX + rect.left, scrollX + window.innerWidth - popupRect.width - 12));
  const top = Math.max(12, scrollY + rect.bottom + 8);

  popup.style.left = `${left}px`;
  popup.style.top = `${top}px`;

  if (activeTipNode && activeTipNode !== tipNode) {
    activeTipNode.removeAttribute("data-open");
  }
  activeTipNode = tipNode;
  tipNode.setAttribute("data-open", "true");
}

function initializeTipInteractions() {
  document.addEventListener("click", (event) => {
    const tipNode = event.target.closest(".tip");
    if (tipNode) {
      event.preventDefault();
      if (activeTipNode === tipNode) {
        hideTipPopup();
      } else {
        showTipPopup(tipNode);
      }
      return;
    }

    const popup = ensureTipPopup();
    if (!popup.hidden && !event.target.closest("#tip-popup")) {
      hideTipPopup();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideTipPopup();
      return;
    }

    const target = event.target;
    if (!target || !target.classList || !target.classList.contains("tip")) {
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    if (activeTipNode === target) {
      hideTipPopup();
    } else {
      showTipPopup(target);
    }
  });
}

function refreshTipA11y() {
  document.querySelectorAll(".tip").forEach((node) => {
    if (!node.hasAttribute("tabindex")) {
      node.setAttribute("tabindex", "0");
    }
    node.setAttribute("role", "button");
    const title = String(node.getAttribute("title") || "").trim();
    if (title) {
      node.setAttribute("aria-label", `Info: ${title}`);
    }
  });
}

function setStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.className = isError ? "error" : "ok";
}

function setProgressState(active, label = "") {
  progressBarNode.classList.toggle("active", active);
  progressLabelNode.textContent = label || (active ? "En cours" : "Pret");
}

function safeParseJson(text, fallback = null) {
  if (!text || !text.trim()) return fallback;
  return JSON.parse(text);
}

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function coalesce(value, fallback) {
  return value === undefined || value === null ? fallback : value;
}

function escapeHtml(value) {
  return String(coalesce(value, ""))
    .split("&")
    .join("&amp;")
    .split("<")
    .join("&lt;")
    .split(">")
    .join("&gt;")
    .split('"')
    .join("&quot;")
    .split("'")
    .join("&#39;");
}

function parseCommaSeparatedList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function readRequiredInt(id) {
  return Number(document.getElementById(id).value);
}

function readOptionalNumber(node) {
  const raw = String(node && node.value ? node.value : "").trim();
  if (!raw) return null;
  return Number(raw);
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

function renderGenerationMode() {
  const select = document.getElementById("generation-mode");
  const hint = document.getElementById("generation-mode-hint");
  select.value = state.generationMode || "llm";
  hint.textContent =
    state.generationMode === "deterministic"
      ? "Mode sans LLM actif: la generation utilise la matrice deterministe locale."
      : "Mode LLM actif: la generation utilise le provider configure et les garde-fous cout/tokens.";
}

function renderAudioMode() {
  const select = document.getElementById("audio-mode");
  const hint = document.getElementById("audio-mode-hint");
  select.value = state.audioMode || "local";
  hint.textContent =
    state.audioMode === "cloud"
      ? "Mode audio cloud actif: le MP3 sera delegue a un provider externe quand il sera configure."
      : "Mode audio local actif: Piper est utilise pour produire le MP3 telechargeable.";
}

function renderDeterministicSettings() {
  const globalSettings = state.deterministic.global || {};
  const scoring = globalSettings.scoring_weights || {};
  const extractive = globalSettings.extractive_rules || {};
  const trimPolicy = globalSettings.trim_policy || {};
  const fallbackPolicy = globalSettings.fallback_policy || {};
  const container = document.getElementById("deterministic-category-settings");
  container.innerHTML = "";

  document.getElementById("det-version").value = coalesce(globalSettings.version, 1);
  document.getElementById("det-target-duration").value = coalesce(globalSettings.target_duration_sec, 600);
  document.getElementById("det-speech-rate").value = coalesce(globalSettings.speech_rate_wpm, 155);
  document.getElementById("det-freshness-hours").value = coalesce(globalSettings.freshness_hours_max, 48);
  document.getElementById("det-min-items").value = coalesce(globalSettings.min_items_per_category_default, 1);
  document.getElementById("det-max-items").value = coalesce(globalSettings.max_items_per_category_default, 3);

  document.getElementById("det-score-freshness").value = coalesce(scoring.freshness, 0.45);
  document.getElementById("det-score-credibility").value = coalesce(scoring.sourceCredibility, 0.3);
  document.getElementById("det-score-richness").value = coalesce(scoring.textRichness, 0.15);
  document.getElementById("det-score-diversity").value = coalesce(scoring.diversity, 0.1);

  document.getElementById("det-extractive-max-sentences").value = coalesce(extractive.maxSentencesPerItem, 2);
  document.getElementById("det-extractive-min-chars").value = coalesce(extractive.minSentenceChars, 40);
  document.getElementById("det-extractive-max-chars").value = coalesce(extractive.maxSentenceChars, 220);
  document.getElementById("det-brief-seconds").value = coalesce(extractive.briefSecondsTarget, 45);
  document.getElementById("det-extractive-strip-quotes").checked = Boolean(extractive.stripQuotesIfLong);
  document.getElementById("det-duration-alignment-enabled").checked = Boolean(extractive.durationAlignmentEnabled);

  document.getElementById("det-trim-step").value = coalesce(trimPolicy.stepSec, 15);
  document.getElementById("det-trim-hard-floor").value = coalesce(trimPolicy.hardFloorSec, 540);
  document.getElementById("det-trim-order").value = Array.isArray(trimPolicy.order) ? trimPolicy.order.join(", ") : "";

  document.getElementById("det-fallback-add").value = Array.isArray(fallbackPolicy.ifTooShortAdd)
    ? fallbackPolicy.ifTooShortAdd.join(", ")
    : "";
  document.getElementById("det-fallback-no-items").value = coalesce(fallbackPolicy.ifNoItems, "skipCategoryAndRebalance");

  document.getElementById("det-scoring-json").value = prettyJson(scoring);
  document.getElementById("det-extractive-json").value = prettyJson(extractive);
  document.getElementById("det-trim-json").value = prettyJson(trimPolicy);
  document.getElementById("det-fallback-json").value = prettyJson(fallbackPolicy);

  state.deterministic.categories.forEach((setting) => {
    const templates = setting.templates || {};
    const scoringOverride = setting.scoring_override || {};
    const templateIntro = coalesce(templates.intro, "");
    const templateImpact = coalesce(templates.impact, "");
    const templateTransition = coalesce(templates.transition, "");
    const card = document.createElement("div");
    card.className = "deterministic-card";
    card.innerHTML = `
      <h3>${escapeHtml(setting.category_name)}</h3>
      <p class="card-meta">Configuration locale prioritaire pour cette categorie.</p>
      <div class="det-card-grid">
        <label class="checkbox-line" for="det-enabled-${escapeHtml(setting.category_id)}">
          <input id="det-enabled-${escapeHtml(setting.category_id)}" type="checkbox" data-field="enabled" ${setting.enabled ? "checked" : ""} /> Active
        </label>
        <span></span>

        <label>Poids editorial <span class="tip" title="Plus la valeur est elevee, plus cette categorie prend de place dans l'episode.">?</span></label>
        <input type="number" min="1" data-field="weight" value="${coalesce(setting.weight, 1)}" />

        <label>Max items (override) <span class="tip" title="Laisse vide pour utiliser la valeur globale.">?</span></label>
        <input type="number" min="1" max="10" data-field="max_items" value="${coalesce(setting.max_items, "")}" />

        <label class="full">Template intro</label>
        <input class="full" type="text" data-field="template_intro" value="${escapeHtml(templateIntro)}" placeholder="Ex: Cote innovation, voici ce qui change..." />

        <label class="full">Template impact principal</label>
        <input class="full" type="text" data-field="template_impact" value="${escapeHtml(templateImpact)}" placeholder="Ex: Pourquoi c'est important maintenant..." />

        <label class="full">Template transition</label>
        <input class="full" type="text" data-field="template_transition" value="${escapeHtml(templateTransition)}" placeholder="Ex: On passe a la categorie suivante..." />

        <label>Score fraicheur</label>
        <input type="number" min="0" max="1" step="0.05" data-field="score_freshness" value="${coalesce(scoringOverride.freshness, "")}" />

        <label>Score credibilite</label>
        <input type="number" min="0" max="1" step="0.05" data-field="score_credibility" value="${coalesce(scoringOverride.sourceCredibility, "")}" />

        <label>Score richesse</label>
        <input type="number" min="0" max="1" step="0.05" data-field="score_richness" value="${coalesce(scoringOverride.textRichness, "")}" />

        <label>Score diversite</label>
        <input type="number" min="0" max="1" step="0.05" data-field="score_diversity" value="${coalesce(scoringOverride.diversity, "")}" />

        <details class="full">
          <summary>Mode avance JSON</summary>
          <div class="stack">
            <label>Templates JSON</label>
            <textarea rows="4" spellcheck="false" data-field="templates">${escapeHtml(prettyJson(templates))}</textarea>
            <label>Scoring override JSON</label>
            <textarea rows="4" spellcheck="false" data-field="scoring_override">${escapeHtml(prettyJson(scoringOverride))}</textarea>
          </div>
        </details>

        <button class="full" type="button" data-action="save-category" data-category-id="${escapeHtml(setting.category_id)}">Sauver categorie</button>
      </div>
    `;
    container.appendChild(card);
  });

  refreshTipA11y();
}

async function reloadAll() {
  const [categories, sources, mappings, settings, schedule, mode, audioMode, deterministic] = await Promise.all([
    api("/api/categories"),
    api("/api/rss-sources"),
    api("/api/mappings"),
    api("/api/settings/duration-target"),
    api("/api/settings/schedule"),
    api("/api/settings/mode"),
    api("/api/settings/audio-mode"),
    api("/api/settings/deterministic"),
  ]);
  state.categories = categories;
  state.sources = sources;
  state.mappings = mappings;
  state.generationMode = mode.generation_mode;
  state.audioMode = audioMode.audio_generation_mode;
  state.deterministic = deterministic;
  state.settings = {
    ...state.settings,
    ...settings,
    ...schedule,
  };
  renderCategories();
  renderSources();
  renderMappings();
  renderGenerationMode();
  renderAudioMode();
  renderDeterministicSettings();
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

function renderGeneratedScript(payload) {
  const output = document.getElementById("script-output");
  const audioStatus = document.getElementById("audio-status");
  const audioDownload = document.getElementById("audio-download");
  const header = `Mode: ${payload.mode_used || "n/a"} | Job: ${payload.job_id || "n/a"}`;
  output.textContent = `${header}\n\n${payload.script || "(script vide)"}`;
  audioStatus.textContent = "Aucun audio genere";
  audioDownload.hidden = true;
}

function generatedScriptTextOnly() {
  const output = document.getElementById("script-output").textContent || "";
  const separator = "\n\n";
  const parts = output.split(separator);
  if (parts.length < 2) {
    return output;
  }
  return parts.slice(1).join(separator).trim();
}

function renderScheduleSummary(schedule) {
  const summary = document.getElementById("schedule-summary");
  const nextRuns = (schedule.next_runs || []).slice(0, 3).join("\n");
  const episodesPerWeekHint =
    schedule.episodes_per_week_hint === undefined || schedule.episodes_per_week_hint === null
      ? "n/a"
      : schedule.episodes_per_week_hint;
  summary.textContent = `Episodes/semaine (estimation): ${episodesPerWeekHint}\nProchains runs:\n${nextRuns || "aucun"}`;
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

document.getElementById("generation-mode-save").addEventListener("click", async () => {
  try {
    const updated = await api("/api/settings/mode", {
      method: "PUT",
      body: JSON.stringify({ generation_mode: document.getElementById("generation-mode").value }),
    });
    state.generationMode = updated.generation_mode;
    renderGenerationMode();
    await reloadOps();
    setStatus(`Mode mis a jour: ${updated.generation_mode}`);
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("audio-mode-save").addEventListener("click", async () => {
  try {
    const updated = await api("/api/settings/audio-mode", {
      method: "PUT",
      body: JSON.stringify({ audio_generation_mode: document.getElementById("audio-mode").value }),
    });
    state.audioMode = updated.audio_generation_mode;
    renderAudioMode();
    setStatus(`Mode audio mis a jour: ${updated.audio_generation_mode}`);
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("deterministic-refresh").addEventListener("click", async () => {
  try {
    const deterministic = await api("/api/settings/deterministic");
    state.deterministic = deterministic;
    renderDeterministicSettings();
    setStatus("Matrice deterministe rechargee");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("deterministic-global-save").addEventListener("click", async () => {
  try {
    const current = state.deterministic.global || {};

    const baseScoring = {
      ...(current.scoring_weights || {}),
      freshness: Number(document.getElementById("det-score-freshness").value),
      sourceCredibility: Number(document.getElementById("det-score-credibility").value),
      textRichness: Number(document.getElementById("det-score-richness").value),
      diversity: Number(document.getElementById("det-score-diversity").value),
    };
    const scoringAdvanced = safeParseJson(document.getElementById("det-scoring-json").value, {});

    const baseExtractive = {
      ...(current.extractive_rules || {}),
      maxSentencesPerItem: Number(document.getElementById("det-extractive-max-sentences").value),
      minSentenceChars: Number(document.getElementById("det-extractive-min-chars").value),
      maxSentenceChars: Number(document.getElementById("det-extractive-max-chars").value),
      briefSecondsTarget: Number(document.getElementById("det-brief-seconds").value),
      stripQuotesIfLong: document.getElementById("det-extractive-strip-quotes").checked,
      durationAlignmentEnabled: document.getElementById("det-duration-alignment-enabled").checked,
    };
    const extractiveAdvanced = safeParseJson(document.getElementById("det-extractive-json").value, {});

    const baseTrimPolicy = {
      ...(current.trim_policy || {}),
      order: parseCommaSeparatedList(document.getElementById("det-trim-order").value),
      stepSec: Number(document.getElementById("det-trim-step").value),
      hardFloorSec: Number(document.getElementById("det-trim-hard-floor").value),
    };
    const trimAdvanced = safeParseJson(document.getElementById("det-trim-json").value, {});

    const baseFallbackPolicy = {
      ...(current.fallback_policy || {}),
      ifTooShortAdd: parseCommaSeparatedList(document.getElementById("det-fallback-add").value),
      ifNoItems: document.getElementById("det-fallback-no-items").value.trim() || "skipCategoryAndRebalance",
    };
    const fallbackAdvanced = safeParseJson(document.getElementById("det-fallback-json").value, {});

    const payload = {
      ...current,
      version: readRequiredInt("det-version"),
      target_duration_sec: readRequiredInt("det-target-duration"),
      speech_rate_wpm: readRequiredInt("det-speech-rate"),
      freshness_hours_max: readRequiredInt("det-freshness-hours"),
      min_items_per_category_default: readRequiredInt("det-min-items"),
      max_items_per_category_default: readRequiredInt("det-max-items"),
      scoring_weights: {
        ...baseScoring,
        ...scoringAdvanced,
      },
      extractive_rules: {
        ...baseExtractive,
        ...extractiveAdvanced,
      },
      trim_policy: {
        ...baseTrimPolicy,
        ...trimAdvanced,
      },
      fallback_policy: {
        ...baseFallbackPolicy,
        ...fallbackAdvanced,
      },
    };

    if (payload.min_items_per_category_default > payload.max_items_per_category_default) {
      throw new Error("Min items/categorie doit etre <= max items/categorie");
    }

    const updated = await api("/api/settings/deterministic/global", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.deterministic.global = updated;
    renderDeterministicSettings();
    setStatus("Configuration deterministe globale mise a jour");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("deterministic-category-settings").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action='save-category']");
  if (!button) return;
  const card = button.closest(".deterministic-card");
  const categoryId = button.dataset.categoryId;

  try {
    const templatesAdvanced = safeParseJson(card.querySelector("[data-field='templates']").value, {});
    const scoringAdvanced = safeParseJson(card.querySelector("[data-field='scoring_override']").value, {});

    const templates = { ...templatesAdvanced };
    const templateIntro = card.querySelector("[data-field='template_intro']").value.trim();
    const templateImpact = card.querySelector("[data-field='template_impact']").value.trim();
    const templateTransition = card.querySelector("[data-field='template_transition']").value.trim();
    if (templateIntro) {
      templates.intro = templateIntro;
    } else {
      delete templates.intro;
    }
    if (templateImpact) {
      templates.impact = templateImpact;
    } else {
      delete templates.impact;
    }
    if (templateTransition) {
      templates.transition = templateTransition;
    } else {
      delete templates.transition;
    }

    const scoringOverride = { ...scoringAdvanced };
    const freshnessNode = card.querySelector("[data-field='score_freshness']");
    const credibilityNode = card.querySelector("[data-field='score_credibility']");
    const richnessNode = card.querySelector("[data-field='score_richness']");
    const diversityNode = card.querySelector("[data-field='score_diversity']");
    const freshness = readOptionalNumber(freshnessNode);
    const sourceCredibility = readOptionalNumber(credibilityNode);
    const textRichness = readOptionalNumber(richnessNode);
    const diversity = readOptionalNumber(diversityNode);

    if (freshness === null) delete scoringOverride.freshness;
    else scoringOverride.freshness = freshness;
    if (sourceCredibility === null) delete scoringOverride.sourceCredibility;
    else scoringOverride.sourceCredibility = sourceCredibility;
    if (textRichness === null) delete scoringOverride.textRichness;
    else scoringOverride.textRichness = textRichness;
    if (diversity === null) delete scoringOverride.diversity;
    else scoringOverride.diversity = diversity;

    const maxItemsRaw = String(card.querySelector("[data-field='max_items']").value || "").trim();

    const payload = {
      enabled: card.querySelector("[data-field='enabled']").checked,
      weight: Number(card.querySelector("[data-field='weight']").value),
      max_items: maxItemsRaw ? Number(maxItemsRaw) : null,
      templates,
      scoring_override: scoringOverride,
    };
    const updated = await api(`/api/settings/deterministic/categories/${categoryId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    const index = state.deterministic.categories.findIndex((item) => item.category_id === categoryId);
    if (index >= 0) {
      state.deterministic.categories[index] = updated;
    }
    renderDeterministicSettings();
    setStatus(`Categorie deterministe mise a jour: ${updated.category_name}`);
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

document.getElementById("generate-run").addEventListener("click", async () => {
  const button = document.getElementById("generate-run");
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Generation en cours...";
  setStatus("Generation du script en cours...");
  setProgressState(true, "Generation du script...");

  try {
    const categoryIds = state.categories.filter((item) => Boolean(item.enabled)).map((item) => item.id);
    const response = await api("/api/generate/script", {
      method: "POST",
      body: JSON.stringify({
        category_ids: categoryIds,
        duration_target_minutes: Number(document.getElementById("duration-target").value),
      }),
    });
    renderGeneratedScript(response);
    await reloadOps();
    setStatus("Script genere avec succes");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
    setProgressState(false, "Pret");
  }
});

document.getElementById("generate-audio-run").addEventListener("click", async () => {
  const button = document.getElementById("generate-audio-run");
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Generation audio en cours...";
  setStatus("Generation de l'audio en cours...");
  setProgressState(true, "Generation de l'audio...");

  try {
    const scriptText = generatedScriptTextOnly();
    if (!scriptText || scriptText === "Aucun script genere") {
      setStatus("Generer d'abord un script", true);
      return;
    }
    const response = await api("/api/generate/audio", {
      method: "POST",
      body: JSON.stringify({ script_text: scriptText }),
    });
    const audio = response.audio || {};
    const downloadUrl = audio.download_url || audio.audio_download_url;
    const fileName = audio.file_name || audio.audio_file_name;
    const modeUsed = audio.mode_used || audio.audio_mode_used || response.mode_used || "local";
    const audioError = audio.error || response.error;
    const audioStatus = document.getElementById("audio-status");
    const audioDownload = document.getElementById("audio-download");
    if (response.status === "ok" && downloadUrl) {
      audioStatus.textContent = `Audio genere en mode ${modeUsed}.`;
      audioDownload.href = downloadUrl;
      audioDownload.download = fileName || `${response.job_id || "audio"}.mp3`;
      audioDownload.hidden = false;
      setStatus("Audio genere avec succes");
    } else {
      audioStatus.textContent = `Audio indisponible: ${audioError || "erreur inconnue"}`;
      audioDownload.hidden = true;
      setStatus(audioError || "Audio indisponible", true);
    }
    await reloadOps();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
    setProgressState(false, "Pret");
  }
});

document.getElementById("copy-script").addEventListener("click", async () => {
  try {
    const text = generatedScriptTextOnly();
    if (!text || text === "Aucun script genere") {
      setStatus("Aucun script a copier", true);
      return;
    }
    await navigator.clipboard.writeText(text);
    setStatus("Script copie dans le presse-papiers");
  } catch (error) {
    setStatus("Copie impossible: verifier les permissions du navigateur", true);
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

initializeTipInteractions();
refreshTipA11y();
reloadAll().catch((error) => setStatus(error.message, true));
