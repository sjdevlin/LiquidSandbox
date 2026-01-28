import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------------------------------------
# 1. Load the CSV that sits in the same directory as this file
# -----------------------------------------------------------
try:
    # Works when the script is run as a .py file
    csv_path = Path(__file__).with_name("ios.csv")
except NameError:
    # Fallback for interactive / notebook sessions
    csv_path = Path("ios.csv")

df = pd.read_csv(
    csv_path,
    header=None,
    names=["Well", "Minute", "Target", "Actual", "PWM"]  # column labels
)

# -----------------------------------------------------------
# 2. Plot 1 – Well A: target (red) vs actual (blue)
# -----------------------------------------------------------
well_a = df[df["Well"] == "A"]

fig1, ax1 = plt.subplots(figsize=(8, 6))
ax1.plot(well_a["Minute"], well_a["Target"], color="red", label="Target (A)")
ax1.plot(well_a["Minute"], well_a["Actual"], color="blue", label="Actual (A)")

ax1.set_xlabel("Elapsed Minute")
ax1.set_ylabel("Temperature (°C)")
ax1.set_ylim(20, 70)     
ax1.set_title("Well A – Target vs Actual Temperature")
ax1.legend()
ax1.grid(True)


    # Save as PNG file
output_file = "poster.png"
plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches='tight', transparent=True)
print(f"Saved: {output_file}")
plt.close()  # Close the figure to free memory
