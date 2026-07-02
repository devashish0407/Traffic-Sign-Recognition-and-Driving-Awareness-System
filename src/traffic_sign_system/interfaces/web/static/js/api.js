/**
 * HTTP API client wrapper.
 */

const MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024; // 200 MB

export async function fetchHazardRules() {
  const resp = await fetch('/api/hazard_rules');
  if (!resp.ok) throw new Error(`HTTP Error: ${resp.status}`);
  return await resp.json();
}

export async function fetchSessionSummary() {
  const resp = await fetch('/api/summary');
  if (!resp.ok) throw new Error(`HTTP Error: ${resp.status}`);
  return await resp.json();
}

export function exportCSV(sessionId = null) {
  let url = '/api/download/csv';
  if (sessionId) {
    url += `?session_id=${encodeURIComponent(sessionId)}`;
  }
  window.location.href = url;
}

export function uploadVideo(file, onProgress) {
  return new Promise((resolve, reject) => {
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      return reject(new Error('File exceeds the maximum upload limit of 200 MB.'));
    }

    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('video', file);

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      let responseData;
      try {
        responseData = JSON.parse(xhr.responseText);
      } catch (err) {
        responseData = { error: 'Unknown server error' };
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(responseData);
      } else {
        const errMsg = responseData.error || `Upload failed with status ${xhr.status}`;
        reject(new Error(errMsg));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network upload failed.')));
    xhr.addEventListener('abort', () => reject(new Error('Upload cancelled.')));

    xhr.open('POST', '/api/upload');
    xhr.send(formData);
  });
}
