metadata = {
    "protocolName": "Nanostar Phase Study",
    "author": "S.Devlin",
    "description": "Heat sources to 65°C, distribute oil with P300, then water+mix with P20 (new tip each).",
    "apiLevel": "2.15",
}

from typing import List
from opentrons import protocol_api


# ----------------------------
# User-tunable configuration
# ----------------------------

# Module + temperature
TEMPMOD_SLOT = "10"          # Ensure this slot is valid for your module on OT-2
TEMPERATURE_C = 65.0
HOLD_MINUTES = 5.0           # time to wait AFTER reaching setpoint (keeps module at 65°C)

# Labware load-names / slots
DEST_LABWARE_LOAD_NAME = "custom_36_well_annealer"   # <-- replace with your actual custom labware load name
DEST_LABWARE_SLOT = "1"

HEATED_BLOCK_LOAD_NAME = "opentrons_24_aluminumblock_eppendorf_1.5ml_safelock_snapcap"  # 1.5 mL Eppendorf
OIL_SOURCE_WELL = "A1"
WATER_SOURCE_WELL = "A2"

# Tip racks
TIPRACK20_LOAD_NAME = "opentrons_96_tiprack_20ul"
TIPRACK20_SLOT = "2"

TIPRACK300_LOAD_NAME = "opentrons_96_tiprack_300ul"
TIPRACK300_SLOT = "5"

# Pipettes
P20_MODEL = "p20_single_gen2"
P20_MOUNT = "left"
# P20 flow/clearances (from your YAML)
P20_ASPIRATE_RATE = 7.0      # µL/s
P20_DISPENSE_RATE = 25.0     # µL/s
P20_ASPIRATE_CLEARANCE_MM = 1.0
P20_DISPENSE_CLEARANCE_MM = 1.0
P20_BLOWOUT_TO_TRASH = True

P300_MODEL = "p300_single_gen2"  # <-- you said “single 300 µL pipette”
P300_MOUNT = "right"
# P300 flow/clearances (based on your YAML, adjusted for single)
P300_ASPIRATE_RATE = 10.0    # µL/s
P300_DISPENSE_RATE = 100.0   # µL/s
P300_ASPIRATE_CLEARANCE_MM = 2.0
P300_DISPENSE_CLEARANCE_MM = 2.0
P300_BLOWOUT_TO_TRASH = True

# Air-gaps and prewet (can be 0 to disable)
OIL_AIR_GAP_UL = 2.0
OIL_PREWET_CYCLES = 2

WATER_AIR_GAP_UL = 1.0
WATER_PREWET_CYCLES = 1

# Volumes & mixing
OIL_VOL_UL = 28.0
WATER_VOL_UL = 1.5
MIX_CYCLES = 30
MIX_VOL_UL = 20.0
MIX_CLEARANCE_MM = 1.0   # keep the tip just off the bottom during mixing

# Samples (destination wells on your custom 36-well plate)
SAMPLE_WELL_NAMES: List[str] = [
    "A1","A2","A3","A4","A5","A6",
    "C1","C2","C3","C4","C5","C6",
]


# ----------------------------
# Helper functions
# ----------------------------

def prewet_tip(pipette: protocol_api.InstrumentContext,
               source,
               cycles: int,
               vol_ul: float) -> None:
    """Aspirate/dispense back to source to condition inner tip walls."""
    if cycles <= 0 or vol_ul <= 0:
        return
    for _ in range(cycles):
        pipette.aspirate(vol_ul, source.bottom(P20_ASPIRATE_CLEARANCE_MM if pipette.max_volume <= 20 else P300_ASPIRATE_CLEARANCE_MM))
        pipette.dispense(vol_ul, source.top())  # dispense to top to avoid over-pressurizing bottom


def set_flow_rates(pipette: protocol_api.InstrumentContext,
                   aspirate_ul_s: float,
                   dispense_ul_s: float) -> None:
    pipette.flow_rate.aspirate = aspirate_ul_s
    pipette.flow_rate.dispense = dispense_ul_s


def resolve_wells(labware: protocol_api.labware.Labware,
                  names: List[str]) -> List[protocol_api.labware.Well]:
    wbn = labware.wells_by_name()
    return [wbn[n] for n in names]


# ----------------------------
# Protocol run
# ----------------------------

def run(ctx: protocol_api.ProtocolContext) -> None:
    # --- Load hardware: module, labware, tips, instruments ---
    # Temperature module (GEN2) with heated block
    temp_module = ctx.load_module("temperature module gen2", TEMPMOD_SLOT)
    heated_block = temp_module.load_labware(HEATED_BLOCK_LOAD_NAME, label="heated_sources")

    # Destination plate (custom 36-well)
    dest_plate = ctx.load_labware(DEST_LABWARE_LOAD_NAME, DEST_LABWARE_SLOT, label="dest_plate")

    # Tip racks
    tiprack20 = ctx.load_labware(TIPRACK20_LOAD_NAME, TIPRACK20_SLOT)
    tiprack300 = ctx.load_labware(TIPRACK300_LOAD_NAME, TIPRACK300_SLOT)

    # Instruments
    p20 = ctx.load_instrument(P20_MODEL, P20_MOUNT, tip_racks=[tiprack20])
    p300 = ctx.load_instrument(P300_MODEL, P300_MOUNT, tip_racks=[tiprack300])

    # Set flow rates
    set_flow_rates(p20, P20_ASPIRATE_RATE, P20_DISPENSE_RATE)
    set_flow_rates(p300, P300_ASPIRATE_RATE, P300_DISPENSE_RATE)

    # Sources & destinations
    oil_src = heated_block.wells_by_name()[OIL_SOURCE_WELL]
    water_src = heated_block.wells_by_name()[WATER_SOURCE_WELL]
    dest_wells = resolve_wells(dest_plate, SAMPLE_WELL_NAMES)

    # --- Pre-heat to setpoint and hold ---
    ctx.comment(f"Setting temperature module to {TEMPERATURE_C:.1f} °C.")
    temp_module.set_temperature(TEMPERATURE_C)  # blocks until reached
    ctx.comment(f"Holding at {TEMPERATURE_C:.1f} °C for {HOLD_MINUTES} minutes to equilibrate.")
    ctx.delay(minutes=HOLD_MINUTES)
    ctx.comment("Proceeding to dispensing steps while maintaining temperature.")

    # ----------------------------
    # Step 1: Oil to all samples (single 300 µL tip for entire run)
    # ----------------------------
    ctx.comment(f"Distributing oil: {OIL_VOL_UL} µL to {len(dest_wells)} wells with one P300 tip.")

    p300.pick_up_tip()
    # Optional prewet for viscous oil
    prewet_tip(p300, oil_src, OIL_PREWET_CYCLES, min(100.0, max(30.0, OIL_VOL_UL * 2)))

    for w in dest_wells:
        # Aspirate oil
        p300.aspirate(OIL_VOL_UL, oil_src.bottom(P300_ASPIRATE_CLEARANCE_MM))
        if OIL_AIR_GAP_UL > 0:
            p300.air_gap(OIL_AIR_GAP_UL)

        # Dispense into destination
        p300.dispense(OIL_VOL_UL + OIL_AIR_GAP_UL, w.bottom(P300_DISPENSE_CLEARANCE_MM))

        # Optional: slight settle time for viscous liquid
        ctx.delay(seconds=0.5)

    # Blow out and drop tip
    if P300_BLOWOUT_TO_TRASH:
        p300.blow_out(ctx.fixed_trash['A1'].top())
    else:
        p300.blow_out(oil_src.top())
    p300.drop_tip()

    # ----------------------------
    # Step 2: Water + mix for each sample (new P20 tip per well)
    # ----------------------------
    ctx.comment(f"Adding water ({WATER_VOL_UL} µL) then mixing {MIX_CYCLES}× @ {MIX_VOL_UL} µL per well with new P20 tip each.")

    for w in dest_wells:
        p20.pick_up_tip()

        # Optional prewet for water
        prewet_tip(p20, water_src, WATER_PREWET_CYCLES, min(15.0, max(5.0, WATER_VOL_UL * 5)))

        # Aspirate water
        p20.aspirate(WATER_VOL_UL, water_src.bottom(P20_ASPIRATE_CLEARANCE_MM))
        if WATER_AIR_GAP_UL > 0:
            p20.air_gap(WATER_AIR_GAP_UL)

        # Dispense into sample well
        p20.dispense(WATER_VOL_UL + WATER_AIR_GAP_UL, w.bottom(P20_DISPENSE_CLEARANCE_MM))

        # In-well mix without leaving the well
        # pipette.mix keeps the tip at the given location between cycles.
        mix_location = w.bottom(MIX_CLEARANCE_MM)
        p20.mix(repetitions=MIX_CYCLES, volume=MIX_VOL_UL, location=mix_location)

        # Optional settle
        ctx.delay(seconds=0.5)

        # Blow out (to trash per your preference) and drop tip
        if P20_BLOWOUT_TO_TRASH:
            p20.blow_out(ctx.fixed_trash['A1'].top())
        else:
            p20.blow_out(w.top())

        p20.drop_tip()

    ctx.comment("Protocol complete. Temperature module remains at setpoint; deactivate if desired.")
    # temp_module.deactivate()  # uncomment if you want to turn it off at the end
