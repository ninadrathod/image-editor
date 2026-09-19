/**
 * Frontend entry — wires UI events to the blur API client.
 */
import { blurImage } from "./js/api.js";
import { isImageFile, createObjectUrl, revokeObjectUrl } from "./js/image.js";

const API_BASE = "http://localhost:8000";

const els = {
  input: document.getElementById("image-input"),
  dropZone: document.getElementById("drop-zone"),
  uploadPrompt: document.getElementById("upload-prompt"),
  previewOriginal: document.getElementById("preview-original"),
  previewBlurred: document.getElementById("preview-blurred"),
  resultPlaceholder: document.getElementById("result-placeholder"),
  blurBtn: document.getElementById("blur-btn"),
  downloadBtn: document.getElementById("download-btn"),
  loading: document.getElementById("loading"),
  fileError: document.getElementById("file-error"),
  apiError: document.getElementById("api-error"),
  fileMeta: document.getElementById("file-meta"),
};

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

let selectedFile = null;
let originalUrl = null;
let blurredUrl = null;

function showError(el, message) {
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError(el) {
  el.textContent = "";
  el.classList.add("hidden");
}

function resetResult() {
  if (blurredUrl) {
    revokeObjectUrl(blurredUrl);
    blurredUrl = null;
  }
  els.previewBlurred.classList.add("hidden");
  els.previewBlurred.removeAttribute("src");
  els.resultPlaceholder.classList.remove("hidden");
  els.downloadBtn.classList.add("hidden");
  els.downloadBtn.removeAttribute("href");
}

function setSelectedFile(file) {
  clearError(els.fileError);
  clearError(els.apiError);
  resetResult();

  if (!file) {
    selectedFile = null;
    els.blurBtn.disabled = true;
    els.previewOriginal.classList.add("hidden");
    els.previewOriginal.removeAttribute("src");
    els.uploadPrompt.classList.remove("hidden");
    els.dropZone.classList.remove("drop-zone--filled");
    clearFileMeta();
    return;
  }

  if (!isImageFile(file)) {
    selectedFile = null;
    els.blurBtn.disabled = true;
    els.previewOriginal.classList.add("hidden");
    els.previewOriginal.removeAttribute("src");
    els.uploadPrompt.classList.remove("hidden");
    els.dropZone.classList.remove("drop-zone--filled");
    clearFileMeta();
    showError(els.fileError, "Please choose an image file (PNG, JPG, WEBP, or GIF).");
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
  els.blurBtn.disabled = false;
}

function setLoading(isLoading) {
  els.loading.classList.toggle("hidden", !isLoading);
  els.blurBtn.disabled = isLoading || !selectedFile;
}

async function handleBlur() {
  if (!selectedFile) return;

  clearError(els.apiError);
  setLoading(true);

  try {
    const blob = await blurImage(API_BASE, selectedFile);
    if (blurredUrl) revokeObjectUrl(blurredUrl);
    blurredUrl = createObjectUrl(blob);

    els.previewBlurred.src = blurredUrl;
    els.previewBlurred.classList.remove("hidden");
    els.resultPlaceholder.classList.add("hidden");
    els.downloadBtn.href = blurredUrl;
    els.downloadBtn.classList.remove("hidden");
  } catch (err) {
    showError(els.apiError, err.message || "Something went wrong. Is the server running?");
  } finally {
    setLoading(false);
  }
}

/* —— Event listeners —— */

els.input.addEventListener("change", () => {
  setSelectedFile(els.input.files?.[0] ?? null);
});

els.blurBtn.addEventListener("click", handleBlur);

["dragenter", "dragover"].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    els.dropZone.classList.add("drop-zone--active");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    els.dropZone.classList.remove("drop-zone--active");
  });
});

els.dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer?.files?.[0] ?? null;
  if (file) {
    // Keep the file input in sync for accessibility / form state
    const dt = new DataTransfer();
    dt.items.add(file);
    els.input.files = dt.files;
    setSelectedFile(file);
  }
});
