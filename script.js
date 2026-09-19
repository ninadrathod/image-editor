/**
 * Frontend entry — preset gallery, keyword search, upload, and apply-preset generate flow.
 * All session state is in-memory; a page refresh clears upload + result.
 */
import { applyPreset, searchPresets } from "./js/api.js";
import { isImageFile, createObjectUrl, revokeObjectUrl } from "./js/image.js";

const API_BASE = "http://localhost:8000";
const PRESETS_MANIFEST = "previews/presets.json";
const SEARCH_DEBOUNCE_MS = 180;

/** Allowed relative paths for gallery thumbnails (no schemes / traversal). */
const PREVIEW_PATH_RE =
  /^previews\/(pre-edit|post-edit)\/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpe?g|png|webp|gif)$/i;

/** DB / JSON preset_name shape used by this project. */
const PRESET_NAME_RE = /^[a-z][a-z0-9_]{0,63}$/;

const els = {
  presetGrid: document.getElementById("preset-grid"),
  presetLoading: document.getElementById("preset-loading"),
  presetError: document.getElementById("preset-error"),
  presetHint: document.getElementById("preset-hint"),
  selectedPresetLabel: document.getElementById("selected-preset-label"),
  presetSearch: document.getElementById("preset-search"),
  searchMeta: document.getElementById("search-meta"),
  searchError: document.getElementById("search-error"),
  input: document.getElementById("image-input"),
  dropZone: document.getElementById("drop-zone"),
  uploadPrompt: document.getElementById("upload-prompt"),
  previewOriginal: document.getElementById("preview-original"),
  previewEdited: document.getElementById("preview-edited"),
  resultPlaceholder: document.getElementById("result-placeholder"),
  generateBtn: document.getElementById("generate-btn"),
  downloadBtn: document.getElementById("download-btn"),
  loading: document.getElementById("loading"),
  fileError: document.getElementById("file-error"),
  apiError: document.getElementById("api-error"),
  fileMeta: document.getElementById("file-meta"),
};

/** @type {string|null} */
let selectedPresetName = null;
/** @type {File|null} */
let selectedFile = null;
/** @type {string|null} */
let originalUrl = null;
/** @type {string|null} */
let editedUrl = null;
/** Bumped when inputs change or a new generate starts — ignores stale responses. */
let generateGeneration = 0;
/** Nested dragenter counter so child nodes don't flicker the drop highlight. */
let dragDepth = 0;
/** @type {Array<{ preset_name: string, pre_edit_image: string, post_edit_image: string }>} */
let allGalleryPresets = [];
/** Bumped on each search keystroke — ignores stale responses. */
let searchGeneration = 0;
/** @type {ReturnType<typeof setTimeout>|null} */
let searchDebounceTimer = null;

function formatPresetLabel(name) {
  return String(name || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * @param {unknown} name
 * @returns {name is string}
 */
function isValidPresetName(name) {
  return typeof name === "string" && PRESET_NAME_RE.test(name);
}

/**
 * Only allow relative gallery paths under previews/pre-edit|post-edit.
 * @param {unknown} path
 * @returns {path is string}
 */
function isSafePreviewPath(path) {
  if (typeof path !== "string" || !path) return false;
  if (path.includes("..") || path.includes("\\") || path.includes("\0")) return false;
  if (path.startsWith("/") || path.startsWith("//")) return false;
  if (/^[a-z][a-z0-9+.-]*:/i.test(path)) return false;
  return PREVIEW_PATH_RE.test(path);
}

function formatFileMeta(file) {
  const kb = file.size / 1024;
  const size = kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(kb))} KB`;
  return `${file.name} · ${size}`;
}

function clearFileMeta() {
  if (!els.fileMeta) return;
  els.fileMeta.textContent = "";
  els.fileMeta.classList.add("hidden");
}

function setFileMeta(file) {
  if (!els.fileMeta) return;
  els.fileMeta.textContent = formatFileMeta(file);
  els.fileMeta.classList.remove("hidden");
  els.fileMeta.title = file.name;
}

function showError(el, message) {
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError(el) {
  el.textContent = "";
  el.classList.add("hidden");
}

function canGenerate() {
  return Boolean(selectedPresetName && selectedFile);
}

function isLoading() {
  return !els.loading.classList.contains("hidden");
}

function updateGenerateEnabled() {
  els.generateBtn.disabled = !canGenerate() || isLoading();
}

function invalidateInFlightGenerate() {
  generateGeneration += 1;
}

function resetResult() {
  invalidateInFlightGenerate();
  els.loading.classList.add("hidden");
  if (editedUrl) {
    revokeObjectUrl(editedUrl);
    editedUrl = null;
  }
  els.previewEdited.classList.add("hidden");
  els.previewEdited.removeAttribute("src");
  els.resultPlaceholder.classList.remove("hidden");
  els.downloadBtn.classList.add("hidden");
  els.downloadBtn.removeAttribute("href");
  els.downloadBtn.setAttribute("download", "edited-image.png");
  updateGenerateEnabled();
}

function setSelectedPreset(name) {
  selectedPresetName = name;
  clearError(els.apiError);
  resetResult();

  /** @type {HTMLElement|null} */
  let activeCard = null;
  const cards = els.presetGrid.querySelectorAll(".preset-card");
  cards.forEach((card) => {
    const isActive = card.dataset.presetName === name;
    card.classList.toggle("preset-card--selected", isActive);
    card.setAttribute("aria-selected", isActive ? "true" : "false");
    if (isActive) activeCard = card;
  });

  if (name) {
    const label = formatPresetLabel(name);
    els.selectedPresetLabel.textContent = label;
    els.selectedPresetLabel.title = name;
    els.presetHint.textContent = `Selected: ${label}`;
    els.presetGrid.setAttribute("aria-activedescendant", `preset-${name}`);
    activeCard?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  } else {
    els.selectedPresetLabel.textContent = "No preset selected";
    els.selectedPresetLabel.removeAttribute("title");
    els.presetHint.textContent = "Hover for original · click to select";
    els.presetGrid.removeAttribute("aria-activedescendant");
  }

  updateGenerateEnabled();
}

function setSelectedFile(file) {
  clearError(els.fileError);
  clearError(els.apiError);
  resetResult();

  if (!file) {
    selectedFile = null;
    if (originalUrl) {
      revokeObjectUrl(originalUrl);
      originalUrl = null;
    }
    els.previewOriginal.classList.add("hidden");
    els.previewOriginal.removeAttribute("src");
    els.uploadPrompt.classList.remove("hidden");
    els.dropZone.classList.remove("drop-zone--filled");
    clearFileMeta();
    updateGenerateEnabled();
    return;
  }

  if (!isImageFile(file)) {
    selectedFile = null;
    if (originalUrl) {
      revokeObjectUrl(originalUrl);
      originalUrl = null;
    }
    els.previewOriginal.classList.add("hidden");
    els.previewOriginal.removeAttribute("src");
    els.uploadPrompt.classList.remove("hidden");
    els.dropZone.classList.remove("drop-zone--filled");
    clearFileMeta();
    showError(els.fileError, "Please choose an image file (PNG, JPG, WEBP, or GIF).");
    updateGenerateEnabled();
    return;
  }

  if (originalUrl) revokeObjectUrl(originalUrl);
  originalUrl = createObjectUrl(file);
  selectedFile = file;

  els.previewOriginal.src = originalUrl;
  els.previewOriginal.classList.remove("hidden");
  els.uploadPrompt.classList.add("hidden");
  els.dropZone.classList.add("drop-zone--filled");
  setFileMeta(file);
  updateGenerateEnabled();
}

function setLoading(loading) {
  els.loading.classList.toggle("hidden", !loading);
  updateGenerateEnabled();
}

async function handleGenerate() {
  if (!canGenerate() || isLoading()) return;

  const presetName = selectedPresetName;
  const file = selectedFile;
  const token = ++generateGeneration;

  clearError(els.apiError);
  setLoading(true);

  try {
    const blob = await applyPreset(API_BASE, presetName, file);
    if (token !== generateGeneration) return;

    if (editedUrl) revokeObjectUrl(editedUrl);
    editedUrl = createObjectUrl(blob);

    els.previewEdited.src = editedUrl;
    els.previewEdited.classList.remove("hidden");
    els.resultPlaceholder.classList.add("hidden");
    els.downloadBtn.href = editedUrl;
    els.downloadBtn.download = `${presetName}-edit.png`;
    els.downloadBtn.classList.remove("hidden");
  } catch (err) {
    if (token !== generateGeneration) return;
    showError(els.apiError, err.message || "Something went wrong. Is the server running?");
  } finally {
    if (token === generateGeneration) {
      setLoading(false);
    }
  }
}

/**
 * @param {{ preset_name: string, pre_edit_image: string, post_edit_image: string }} preset
 */
function createPresetCard(preset) {
  const name = preset.preset_name;
  const label = formatPresetLabel(name);

  const button = document.createElement("button");
  button.type = "button";
  button.id = `preset-${name}`;
  button.className = "preset-card";
  button.dataset.presetName = name;
  button.setAttribute("role", "option");
  const isSelected = name === selectedPresetName;
  button.setAttribute("aria-selected", isSelected ? "true" : "false");
  if (isSelected) button.classList.add("preset-card--selected");
  button.setAttribute(
    "aria-label",
    `Select preset ${label}. Hover or focus to compare with the original photo.`,
  );

  const media = document.createElement("span");
  media.className = "preset-card__media";

  const imgEdited = document.createElement("img");
  imgEdited.className = "preset-card__img preset-card__img--edited";
  imgEdited.src = preset.post_edit_image;
  imgEdited.alt = "";
  imgEdited.loading = "lazy";
  imgEdited.decoding = "async";

  const imgOriginal = document.createElement("img");
  imgOriginal.className = "preset-card__img preset-card__img--original";
  imgOriginal.src = preset.pre_edit_image;
  imgOriginal.alt = "";
  imgOriginal.loading = "lazy";
  imgOriginal.decoding = "async";

  media.append(imgEdited, imgOriginal);

  const nameEl = document.createElement("span");
  nameEl.className = "preset-card__name";
  nameEl.textContent = label;

  button.append(media, nameEl);
  button.addEventListener("click", () => setSelectedPreset(name));
  return button;
}

/**
 * Rebuild the preset preview grid from the given list.
 * @param {Array<{ preset_name: string, pre_edit_image: string, post_edit_image: string }>} presets
 * @param {{ emptyMessage?: string }} [options]
 */
function renderPresetGrid(presets, options = {}) {
  els.presetGrid.replaceChildren();

  if (!presets.length) {
    const empty = document.createElement("p");
    empty.className = "col-span-full text-sm text-mute py-8 text-center";
    empty.textContent = options.emptyMessage || "No presets to show.";
    els.presetGrid.appendChild(empty);
    return;
  }

  for (const preset of presets) {
    els.presetGrid.appendChild(createPresetCard(preset));
  }

  if (selectedPresetName) {
    els.presetGrid.setAttribute("aria-activedescendant", `preset-${selectedPresetName}`);
  }
}

async function loadPresets() {
  clearError(els.presetError);

  try {
    const response = await fetch(PRESETS_MANIFEST);
    if (!response.ok) throw new Error(`Could not load presets (${response.status}).`);

    const presets = await response.json();
    if (!Array.isArray(presets) || presets.length === 0) {
      throw new Error("No presets found in the gallery.");
    }

    els.presetLoading?.remove();
    allGalleryPresets = [];

    let skipped = 0;
    for (const preset of presets) {
      if (
        !isValidPresetName(preset?.preset_name) ||
        !isSafePreviewPath(preset?.pre_edit_image) ||
        !isSafePreviewPath(preset?.post_edit_image)
      ) {
        skipped += 1;
        continue;
      }
      allGalleryPresets.push({
        preset_name: preset.preset_name,
        pre_edit_image: preset.pre_edit_image,
        post_edit_image: preset.post_edit_image,
      });
    }

    if (!allGalleryPresets.length) {
      throw new Error(
        skipped
          ? "No valid presets found (entries failed name or image-path checks)."
          : "No valid presets found in the gallery.",
      );
    }

    renderPresetGrid(allGalleryPresets);
    if (els.searchMeta) els.searchMeta.textContent = "Type to filter presets";
  } catch (err) {
    els.presetLoading?.remove();
    allGalleryPresets = [];
    showError(
      els.presetError,
      err.message || "Could not load the preset gallery.",
    );
  }
}

/**
 * @param {string[]} matchNames
 */
function applySearchFilter(matchNames) {
  const allowed = new Set(matchNames.filter((n) => isValidPresetName(n)));
  const filtered = allGalleryPresets.filter((p) => allowed.has(p.preset_name));
  renderPresetGrid(filtered, { emptyMessage: "No presets match that search." });
  if (els.searchMeta) {
    els.searchMeta.textContent = `${filtered.length} match${filtered.length === 1 ? "" : "es"}`;
  }
}

function clearSearchFilter() {
  renderPresetGrid(allGalleryPresets);
  if (els.searchMeta) els.searchMeta.textContent = "Type to filter presets";
}

async function runPresetSearch(query) {
  if (!els.presetSearch) return;

  const q = String(query || "").trim();
  const token = ++searchGeneration;
  clearError(els.searchError);

  if (!q) {
    clearSearchFilter();
    return;
  }

  try {
    const matches = await searchPresets(API_BASE, q);
    if (token !== searchGeneration) return;
    applySearchFilter(matches.map((m) => m.preset_name));
  } catch (err) {
    if (token !== searchGeneration) return;
    clearSearchFilter();
    showError(els.searchError, err.message || "Preset search failed.");
  }
}

function schedulePresetSearch() {
  if (!els.presetSearch) return;
  const value = els.presetSearch.value;
  if (searchDebounceTimer != null) clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    searchDebounceTimer = null;
    runPresetSearch(value);
  }, SEARCH_DEBOUNCE_MS);
}

/* —— Event listeners —— */

els.input.addEventListener("change", () => {
  setSelectedFile(els.input.files?.[0] ?? null);
});

els.generateBtn.addEventListener("click", handleGenerate);

if (els.presetSearch) {
  els.presetSearch.addEventListener("input", schedulePresetSearch);
}

els.dropZone.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragDepth += 1;
  els.dropZone.classList.add("drop-zone--active");
});

els.dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
});

els.dropZone.addEventListener("dragleave", (e) => {
  e.preventDefault();
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) {
    els.dropZone.classList.remove("drop-zone--active");
  }
});

els.dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  els.dropZone.classList.remove("drop-zone--active");

  const file = e.dataTransfer?.files?.[0] ?? null;
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    els.input.files = dt.files;
    setSelectedFile(file);
  }
});

loadPresets();
