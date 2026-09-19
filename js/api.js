/**
 * Talks to The Local Studio backend.
 */

/**
 * POST an image to /api/blur and return the blurred image as a Blob.
 * @param {string} baseUrl - API origin, e.g. http://localhost:8000
 * @param {File} file - Image file selected by the user
 * @returns {Promise<Blob>}
 */
export async function blurImage(baseUrl, file) {
  const form = new FormData();
  form.append("file", file);

  let response;
  try {
    response = await fetch(`${baseUrl}/api/blur`, {
      method: "POST",
      body: form,
    });
  } catch {
    throw new Error("Could not reach the server. Start the backend and try again.");
  }

  if (!response.ok) {
    let detail = "Blur request failed.";
    try {
      const data = await response.json();
      if (data.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }

  return response.blob();
}

/**
 * POST preset name + image to /api/apply-preset and return the result as a Blob.
 * @param {string} baseUrl - API origin, e.g. http://localhost:8000
 * @param {string} presetName - DB preset_name
 * @param {File} file - Image file selected by the user
 * @returns {Promise<Blob>}
 */
export async function applyPreset(baseUrl, presetName, file) {
  const form = new FormData();
  form.append("preset_name", presetName);
  form.append("file", file);

  let response;
  try {
    response = await fetch(`${baseUrl}/api/apply-preset`, {
      method: "POST",
      body: form,
    });
  } catch {
    throw new Error("Could not reach the server. Start the backend and try again.");
  }

  if (!response.ok) {
    let detail = "Apply-preset request failed.";
    try {
      const data = await response.json();
      if (data.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }

  return response.blob();
}
