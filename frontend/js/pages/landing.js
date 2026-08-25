/* ------------------------------- HELPERS ---------------------------------- */
const one = (selector) => document.querySelector(selector);
const all = (selector) => document.querySelectorAll(selector);
const clamp = (value) => Math.max(0, Math.min(1, value));

/* ----------------------------- LIQUID GLASS ------------------------------- */
all("[data-glass]").forEach((button) => {
  const light = button.dataset.glass === "light";

  LiquidGlass.apply(button, {
    bandX: 12,
    bandY: 9,
    strengthY: .82,
    bend: 24,
    dispersion: 6,
    tintTop: light ? "rgba(255,255,255,.72)" : "rgba(30,34,43,.46)",
    tintBottom: light ? "rgba(255,255,255,.44)" : "rgba(10,12,18,.28)",
    fallbackBlur: 16
  });
});

/* ------------------------------- GEMINI TABS ------------------------------ */
const tabs = all(".tab");

tabs.forEach((clickedTab) => {
  clickedTab.addEventListener("click", () => {
    tabs.forEach((tab) => {
      const selected = tab === clickedTab;
      tab.setAttribute("aria-selected", selected);
      one("#" + tab.dataset.panel).hidden = !selected;
    });
  });
});

/* --------------------------- HERO VIDEO CONTROLS -------------------------- */
const videos = window.HERO_VIDEOS || [];
const video = one("#video");
const volume = one("#volume");
const sound = one("#sound");
const slider = one("#volumeSlider");
let videoIndex = 0;

function showSoundState() {
  sound.innerHTML = video.muted ? "&#128263;" : "&#128266;";
  sound.setAttribute("aria-label", video.muted ? "Unmute video" : "Mute video");
}

function playVideo(index) {
  videoIndex = index % videos.length;
  video.src = videos[videoIndex];
  video.play().catch(() => {});
}

if (videos.length) {
  video.loop = videos.length === 1;
  video.volume = .5;
  video.addEventListener("loadeddata", () => {
    video.hidden = false;
    volume.hidden = false;
  });
  video.addEventListener("ended", () => {
    if (videos.length > 1) playVideo(videoIndex + 1);
  });
  video.addEventListener("error", () => {
    video.hidden = true;
    volume.hidden = true;
  });
  playVideo(0);
}

sound.addEventListener("click", () => {
  video.muted = !video.muted;
  showSoundState();
});

slider.addEventListener("input", () => {
  video.volume = slider.value / 100;
  video.muted = video.volume === 0;
  showSoundState();
});

/* ------------------------------ SCROLL EFFECTS ---------------------------- */
const root = document.documentElement;
const hero = one("#hero");
const journey = one("#journey");
const plane = one("#plane");
const stories = all(".story article");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
let pausedByScroll = false;

function updateScroll() {
  const heroProgress = clamp(scrollY / (hero.offsetHeight * .72));

  if (!reducedMotion) {
    root.style.setProperty("--hero-fade", clamp(1 - heroProgress * 1.58));
    root.style.setProperty("--hero-dark", heroProgress * .82);
  }

  if (heroProgress >= .62 && !video.paused) {
    video.pause();
    pausedByScroll = true;
  }
  if (heroProgress <= .24 && pausedByScroll) {
    video.play().catch(() => {});
    pausedByScroll = false;
  }
  if (reducedMotion) return;

  const rect = journey.getBoundingClientRect();
  const navHeight = parseFloat(getComputedStyle(root).getPropertyValue("--nav-height"));
  const progress = clamp((navHeight - rect.top) / Math.max(1, journey.offsetHeight - innerHeight));
  const planeEnd = innerWidth <= 760 ? 75 : 86;
  const activeStory = progress < .34 ? 0 : progress < .68 ? 1 : 2;

  plane.style.left = 9 + progress * (planeEnd - 9) + "%";
  stories.forEach((story, index) => story.classList.toggle("on", index === activeStory));
}

addEventListener("scroll", updateScroll, { passive: true });
addEventListener("resize", updateScroll);
updateScroll();
