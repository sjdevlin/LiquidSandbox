"""
populate_experiment.py
Populate DB with a 2^4 full-factorial DOE (3 replicates, 48 wells)
for Span 80 water-in-oil emulsion screening.

Assumes the model classes in experiment.py / plate.py live
in the same directory (or are import-able on your PYTHONPATH).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from itertools import product
from services import AppConfig, DatabaseService


# ── local model classes ─────────────────────────────────────────
from models import Plate, Experiment, Sample, SampleDetail, Parameter

config = AppConfig("./config.yaml")
db = DatabaseService(config.get("sqlite_db"))

# 3. ── create experiment record ─────────────────────────────────

# 4. ── define Parameters (only created once) ───────────────────
PARAM_DEFS = ["dispense_flowRate","dispense_mix_times","dispense_mmFromBottom","surfactant_fraction"]

param_objs = {}
for name in PARAM_DEFS:
    # Look-up or create so we do not duplicate on re-runs
    param = db.get_parameter_by_name(name)
    param_objs[name] = param

# 5. ── factor levels & Cartesian product (16 combinations) ─────
LEVELS = {
    "dispense_flowRate": [12.5, 25.0],
    "dispense_mix_times": [5, 15],
    "dispense_mmFromBottom": [0.5, 0.1],
    "surfactant_fraction":  [1.25, 2.50],
}
factor_order = list(LEVELS.keys())   # keep key order stable
factor_grid  = list(product(*(LEVELS[f] for f in factor_order)))   # 16 tuples
# ----------------------------------------------------------------

# 6. ── simple well-assignment helper ────────────────────────────
def next_well_coordinates(idx: int):
    """
    Returns (row, column) for a 96-well plate (8 rows × 12 cols),
    filling rows A..H left-to-right, top-to-bottom.

    idx : 0-based linear index
    """
    row = 2 + idx // 20   # 3-22  (A-H)
    col = 2 + idx % 20    # 3-14 (1-12)
    return row, col    # store as integers

# 7. ── populate 48 wells (3 replicates × 16 conditions) ─────────
well_idx = 0
for rep in range(3):                     # replicate blocks
    for combo in factor_grid:            # 16 factorial points
        row, col = next_well_coordinates(well_idx)
        well_idx += 1

        sample = Sample(
            experiment_id=1,
            well_row=row,
            well_column=col,
        )
        sample.id = db.add_sample(sample)
        print(f"Adding sample {sample.id} at ({row}, {col}) with factors {combo}")

        # add parameter values
        for key, value in zip(factor_order, combo):
            sd = SampleDetail(
                sample_id=sample.id,
                parameter_id=param_objs[key].id,
                value=str(value),
            )
            db.add_sample_detail(sd)


# 8. ── commit all objects ───────────────────────────────────────
print(f"✓ 48 samples written")
