// every backend endpoint answers with {success: true, ...} or
// {success: false, error: {code, message}}, so unwrapping it once here keeps
// the calling code readable
async function postJson(url, options, fallbackMessage) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => null);

  if (!res.ok || !data || !data.success) {
    throw new Error((data && data.error && data.error.message) || fallbackMessage);
  }

  return data;
}

// Same envelope contract as postJson, but over XHR: fetch cannot report when
// the request body has finished going up, and that is the boundary that ticks
// row 1 over to row 2. Only the video upload needs it.
function postFormUpload(url, formData, onUploaded, fallbackMessage) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.upload.addEventListener("load", onUploaded);

    xhr.addEventListener("load", () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch (e) { /* handled below */ }

      const ok = xhr.status >= 200 && xhr.status < 300;
      if (!ok || !data || !data.success) {
        reject(new Error((data && data.error && data.error.message) || fallbackMessage));
        return;
      }
      resolve(data);
    });

    xhr.addEventListener("error", () => reject(new Error("The upload didn't reach the server.")));
    xhr.addEventListener("abort", () => reject(new Error("Upload stopped.")));
    xhr.send(formData);
  });
}

/* ---- the analysing state -------------------------------------------------
   The card swaps its two-up chooser for a dial and a three-row ladder while
   the video goes up and Gemini reads it. #status is left to errors only.

   The three rows map to three real boundaries: the request body finishing,
   /api/analyse returning, and /api/packages/match returning. Nothing here is
   on a timer.
   -------------------------------------------------------------------------- */

const DIAL_CIRC = 502.65;   // 2πr for the r=80 ring

function phase(n, state) {
  const row = $("ph" + n);
  row.classList.remove("is-live", "is-done");
  if (state) row.classList.add(state);
}

function phaseMeta(n, text) { $("meta" + n).textContent = text; }
function footSay(text) { $("footHint").textContent = text; }

function formatBytes(n) {
  return n < 1024 * 1024
    ? (n / 1024).toFixed(0) + " KB"
    : (n / 1024 / 1024).toFixed(1) + " MB";
}

function formatClock(seconds) {
  const s = Math.round(seconds);
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}

/* Name, size and length stay on screen the whole way through: confirming the
   right clip went up is the first thing anyone checks when a result looks odd. */
function showFileMeta(file) {
  $("fileName").textContent = file.name;
  $("fileSize").textContent = formatBytes(file.size);

  // duration is not on the File object — the only way to it is to let a video
  // element read the header. Harmless if it fails; the row just shows size.
  const url = URL.createObjectURL(file);
  const probe = document.createElement("video");
  probe.preload = "metadata";
  probe.addEventListener("loadedmetadata", () => {
    if (isFinite(probe.duration)) {
      $("fileLength").textContent = formatClock(probe.duration);
      $("fileLength").hidden = false;
      $("fileDot2").hidden = false;
    }
    URL.revokeObjectURL(url);
  });
  probe.addEventListener("error", () => URL.revokeObjectURL(url));
  probe.src = url;
}

/* what Gemini read, in the few words the ladder has room for */
function summarise(analysis) {
  if (!analysis) return "read";
  const where = (analysis.detected_destinations || [])[0] || analysis.destination_region;
  const vibes = (analysis.travel_style || []).slice(0, 2).join(", ");
  return [where, vibes].filter(Boolean).join(" · ") || "read";
}

function enterAnalysing() {
  const live = $("ringLive");
  document.querySelector(".form-card").classList.add("is-analysing");
  $("dial").classList.remove("is-done");
  $("dial").classList.add("is-sweeping");
  live.style.strokeDasharray = "";
  live.style.strokeDashoffset = "";
  live.style.transition = "";

  $("dialSub").textContent = "Working";
  $("phaseTitle").textContent = "Sending your video";
  phase(1, "is-live"); phase(2, null); phase(3, null);
  phaseMeta(1, "on its way");
  phaseMeta(2, "Gemini");
  phaseMeta(3, "—");
  footSay("This usually takes under a minute. You can leave this tab open.");
}

function leaveAnalysing() {
  document.querySelector(".form-card").classList.remove("is-analysing");
  $("dial").classList.remove("is-sweeping", "is-done");
}

/* run the arc round to a full ring, then let .is-done turn it green */
function closeDial() {
  const live = $("ringLive");
  $("dial").classList.remove("is-sweeping");
  live.style.strokeDasharray = DIAL_CIRC;
  live.style.strokeDashoffset = DIAL_CIRC * 0.18;
  live.style.transition = "stroke-dashoffset .42s var(--ease-out), stroke .5s var(--ease)";
  requestAnimationFrame(() => { live.style.strokeDashoffset = 0; });
  $("dial").classList.add("is-done");
}

async function submitVideo() {
  const input = $("videoInput");
  const link = $("pasteLink").value.trim();

  if (!input.files.length) {
    // /api/analyse takes a multipart file upload; fetching the video behind a
    // link needs a server-side download step that does not exist yet
    $("status").textContent = link
      ? "Link analysis isn't connected yet — please choose a video file for now."
      : "Please choose a video file first.";
    return;
  }

  const file = input.files[0];
  $("status").textContent = "";        // the dial reports progress now; #status is errors only
  $("submitBtn").disabled = true;

  showFileMeta(file);
  enterAnalysing();

  const formData = new FormData();
  formData.append("video", file);

  try {
    // step 1: Gemini reads the video
    const analysis = await postFormUpload(
      "/api/analyse",
      formData,
      () => {                                    // the request body has finished going up
        phase(1, "is-done");
        phase(2, "is-live");
        phaseMeta(1, formatBytes(file.size) + " sent");
        $("phaseTitle").textContent = "Reading the place, pace and mood";
        footSay("Your video is safely uploaded. Gemini is watching it now.");
      },
      "The video could not be analysed."
    );

    // step 2: the analysis is used to search the package database
    phase(2, "is-done");
    phase(3, "is-live");
    phaseMeta(2, summarise(analysis.analysis));
    $("phaseTitle").textContent = "Matching packages";
    $("dialSub").textContent = "Matching";
    footSay("Reading the catalogue for trips that fit.");

    const matches = await postJson(
      "/api/packages/match",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analysis: analysis.analysis })
      },
      "Packages could not be matched."
    );

    // the next two steps are their own pages, so the result rides along in
    // session storage rather than being re-analysed on each one
    sessionStorage.setItem("tripBridgeAnalysis", JSON.stringify(analysis.analysis));
    sessionStorage.setItem("tripBridgePackages", JSON.stringify(matches.packages));

    const found = (matches.packages || []).length;
    phase(3, "is-done");
    phaseMeta(3, found + (found === 1 ? " package" : " packages"));
    $("phaseTitle").textContent = found
      ? found + (found === 1 ? " match found" : " matches found")
      : "No matches found";
    closeDial();
    footSay("Taking you to Insights…");

    // let the ring finish closing before the page changes under it
    setTimeout(() => { window.location.href = "/analysis"; }, 900);
  } catch (err) {
    leaveAnalysing();
    $("submitBtn").disabled = false;
    $("status").textContent = "Error: " + err.message;
  }
}