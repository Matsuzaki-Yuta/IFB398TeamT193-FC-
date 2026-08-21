/* What the flow has collected so far, kept for the life of the tab.
 *
 * Each step is its own page, so stepping back is a fresh document load and the
 * forms come up empty unless something puts the answers back. sessionStorage
 * holds the plain values; the chosen video is a File, which sessionStorage
 * cannot serialise, so it goes to IndexedDB — which stores Blobs directly.
 *
 * Every call is guarded: storage can be unavailable (private browsing, a
 * blocked origin) and a missing cache should cost the user a retype, never a
 * broken page.
 */
var FlowStore = (function () {
  var CUSTOMER = "tripBridgeCustomer";
  var INSPIRATION = "tripBridgeInspiration";
  var QUOTE = "tripBridgeQuote";

  function read(key) {
    try {
      return JSON.parse(sessionStorage.getItem(key)) || {};
    } catch (e) {
      return {};
    }
  }

  // Merge rather than replace, so a page can save one field at a time without
  // having to hold the whole record.
  function patch(key, changes) {
    var next = read(key);
    Object.keys(changes).forEach(function (k) { next[k] = changes[k]; });
    try {
      sessionStorage.setItem(key, JSON.stringify(next));
    } catch (e) { /* quota or disabled storage: nothing to do but carry on */ }
    return next;
  }

  function clear(key) {
    try { sessionStorage.removeItem(key); } catch (e) {}
  }

  // ── the video file ──────────────────────────────────────────────────────────
  var DB_NAME = "tripBridge";
  var DB_STORE = "files";
  var VIDEO_KEY = "video";

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) return reject(new Error("IndexedDB unavailable"));
      var req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(DB_STORE)) {
          req.result.createObjectStore(DB_STORE);
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function withStore(mode, run) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(DB_STORE, mode);
        var req = run(tx.objectStore(DB_STORE));
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { reject(req.error); };
        tx.oncomplete = function () { db.close(); };
      });
    });
  }

  function saveVideo(file) {
    return withStore("readwrite", function (store) {
      return store.put(file, VIDEO_KEY);
    }).catch(function () { /* the picker still holds it for this page */ });
  }

  // Resolves to a File, or null when nothing was stored or storage is closed
  // to us. Callers treat both the same way: show an empty picker.
  function loadVideo() {
    return withStore("readonly", function (store) {
      return store.get(VIDEO_KEY);
    }).then(function (file) {
      return file || null;
    }).catch(function () { return null; });
  }

  function clearVideo() {
    return withStore("readwrite", function (store) {
      return store.delete(VIDEO_KEY);
    }).catch(function () {});
  }

  return {
    CUSTOMER: CUSTOMER,
    INSPIRATION: INSPIRATION,
    QUOTE: QUOTE,
    read: read,
    patch: patch,
    clear: clear,
    saveVideo: saveVideo,
    loadVideo: loadVideo,
    clearVideo: clearVideo
  };
})();
