// IndexedDB-backed draft queue for add-location.html, so a submission
// captured with no connectivity isn't lost -- it's saved locally and
// flushed to the API once back online (or via a manual "Sync now").

const DB_NAME = 'launch-point-drafts';
const STORE_NAME = 'drafts';

function openDraftsDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'localId', autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveDraft(payload) {
  const db = await openDraftsDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.add({ payload, createdAt: new Date().toISOString(), synced: false });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function getUnsyncedDrafts() {
  const db = await openDraftsDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => resolve(req.result.filter((d) => !d.synced));
    req.onerror = () => reject(req.error);
  });
}

async function deleteDraft(localId) {
  const db = await openDraftsDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const req = tx.objectStore(STORE_NAME).delete(localId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// Attempts to POST every queued draft; deletes each on success. Returns
// {synced, failed} counts. Safe to call repeatedly (e.g. on 'online' and
// from a manual "Sync now" button) -- drafts that fail stay queued.
async function flushDrafts(apiBase, token) {
  const drafts = await getUnsyncedDrafts();
  let synced = 0;
  let failed = 0;

  for (const draft of drafts) {
    try {
      const res = await fetch(`${apiBase}/api/submissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(draft.payload),
      });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      await deleteDraft(draft.localId);
      synced++;
    } catch (err) {
      failed++;
    }
  }

  return { synced, failed };
}
