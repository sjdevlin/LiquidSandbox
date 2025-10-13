# gantt_chart_compact.py
# Generate a compact Gantt chart PNG with serif (Times) font and thinner bars.

import matplotlib.pyplot as plt

# ---- Configurable bits ----
tasks = {
    "Platform completion (software & hardware)": (9, 12),
    "Phase diagram mapping (NS + salts/crowding)": (12, 18),
    "FTI characterisation across environments":    (18, 24),
    "Cell-free transcription optimization":        (24, 36),
}
title = "Gantt Chart for Project Timeline"
output_png = "gantt_chart.png"

BAR_HEIGHT = 0.5        # thinner bars (default is 0.8)
FIGSIZE = (9.5, 2.1)     # smaller height overall
BASE_FONTSIZE = 12        # smaller fonts to save space
# ---------------------------

# Use a serif font (Times if present)
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif", "Nimbus Roman", "Liberation Serif"]
plt.rcParams["font.size"] = BASE_FONTSIZE

labels = list(tasks.keys())
spans  = [tasks[k] for k in labels]
starts = [s for (s, e) in spans]
durations = [e - s for (s, e) in spans]

fig, ax = plt.subplots(figsize=FIGSIZE)
ypos = range(len(labels))

# Draw thinner bars
for i, (start, dur) in enumerate(zip(starts, durations)):
    ax.barh(i, dur, left=start, height=BAR_HEIGHT)

# Annotate each bar with its month range (smaller text)
for i, (start, end) in enumerate(spans):
    ax.text(start + (end - start) / 2, i, f"{start}-{end}",
            va="center", ha="center", fontsize=BASE_FONTSIZE-1)

ax.set_yticks(list(ypos))
ax.set_yticklabels(labels)
ax.invert_yaxis()  # Highest-level task at top
ax.set_xlabel("Months", fontsize=BASE_FONTSIZE)
#ax.set_title(title, fontsize=BASE_FONTSIZE+1)

# Tighter tick/label padding to reduce height usage
ax.tick_params(axis="y", pad=2, labelsize=BASE_FONTSIZE-1)
ax.tick_params(axis="x", labelsize=BASE_FONTSIZE-1)

# Set a tidy x-axis range
xmin = min(starts) - 1
xmax = max(s + d for s, d in zip(starts, durations)) + 1
ax.set_xlim(xmin, xmax)

fig.tight_layout()
fig.savefig(output_png, dpi=200, bbox_inches="tight")
print(f"Saved {output_png}")
