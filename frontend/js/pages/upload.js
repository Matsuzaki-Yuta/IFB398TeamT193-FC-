/* Guarded: if the id is missing the call throws and nothing below it runs. */
var submitBtn = document.getElementById("submitBtn");
if (submitBtn) LiquidGlass.apply(submitBtn, {
  bandX: 12, bandY: 9, strengthY: .82, bend: 24, dispersion: 6,
  rimBlur: 1.2, rimSaturate: 1.65,
  centerBlur: 4, centerSaturate: 1.28, centerBrightness: .94,
  tintTop: "rgba(30,34,43,.82)", tintBottom: "rgba(10,12,18,.72)",
  fallbackBlur: 16, fallbackSaturate: 1.55
});

/* Keep the chosen video and the pasted link for the length of the session, so
   stepping back here from the analysis page shows the pick already in place. */
(function () {
  const input = $("videoInput");
  const link = $("pasteLink");

  input.addEventListener("change", () => {
    if (input.files.length) {
      FlowStore.saveVideo(input.files[0]);
      FlowStore.patch(FlowStore.INSPIRATION, { videoName: input.files[0].name });
    } else {
      FlowStore.clearVideo();
      FlowStore.patch(FlowStore.INSPIRATION, { videoName: null });
    }
  });

  link.addEventListener("input", () => {
    FlowStore.patch(FlowStore.INSPIRATION, { link: link.value });
  });

  const saved = FlowStore.read(FlowStore.INSPIRATION);
  if (saved.link) link.value = saved.link;

  // A file input cannot be assigned a path, but it will take a DataTransfer
  // list — so the restored File shows in the native control and submits again
  // without the user re-picking it.
  FlowStore.loadVideo().then((file) => {
    if (!file || input.files.length) return;
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch (e) {
      // no DataTransfer support: say which video was picked, ask for it again
      $("status").textContent =
        "Previously chosen: " + file.name + " — please select it again to re-analyse.";
    }
  });
})();

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

  $("submitBtn").disabled = true;
  $("status").textContent = "Uploading and analysing video with Gemini AI...";

  const formData = new FormData();
  formData.append("video", input.files[0]);

  try {
    // the backend splits this into two steps: Gemini reads the video, then
    // the analysis is used to search the package database
    const analysis = await postJson(
      "/api/analyse",
      { method: "POST", body: formData },
      "The video could not be analysed."
    );

    $("status").textContent = "Analysis complete. Finding matching packages...";

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

    $("status").textContent = "Analysis complete!";
    window.location.href = "/analysis";
  } catch (err) {
    $("status").textContent = "Error: " + err.message;
  } finally {
    $("submitBtn").disabled = false;
  }
}
