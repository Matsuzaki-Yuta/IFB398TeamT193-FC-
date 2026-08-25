Optional hero footage for the home page.

Drop a file named hero.mp4 in this folder and the home page will play it behind
the headline automatically, at 50% opacity under a dark scrim. If the file is
absent the page falls back to the animated colour wash, which is the default
look, so nothing breaks either way.

  static path used by the page:  /static/media/hero.mp4

What works well:
  - 8 to 15 seconds, seamless loop, no hard cuts
  - slow drifting shots (coastline, city at night, aerial over reef)
  - 1920x1080 is plenty; keep it under about 4 MB so it starts fast
  - no on-screen text or logos, the headline sits on top of it
  - encode with:  ffmpeg -i in.mov -vf scale=1920:-2 -c:v libx264 -crf 28 \
                         -preset slow -an -movflags +faststart hero.mp4
    (-an strips the audio track, which is never played)

Use footage you have the right to use. Do not lift clips from a brand's
website for a submitted project.
