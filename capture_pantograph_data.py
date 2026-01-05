#!/usr/bin/env python3
"""Capture stereo RGB + depth + semantic masks for the pantograph scene."""

import os
from isaacsim import SimulationApp

# Headless render; explicit RTX renderer for replicator
simulation_app = SimulationApp(
    {"headless": True, "renderer": "RayTracedLighting", "width": 1920, "height": 1080}
)

import omni.usd
import omni.replicator.core as rep
from pxr import Sdf, Gf, UsdGeom

SCENE_PATH = r"D:\\isaac-sim-standalone-5.1.0-windows-x86_64\\isaac-sim-standalone-5.1.0-windows-x86_64\\pantograph_stereo_scene.usd"
OUTPUT_DIR = r"D:\\isaac-sim-standalone-5.1.0-windows-x86_64\\isaac-sim-standalone-5.1.0-windows-x86_64\\captures"
NUM_FRAMES = 30
RESOLUTION = (1920, 1080)

ctx = omni.usd.get_context()
ctx.open_stage(SCENE_PATH)
stage = ctx.get_stage()
if stage is None:
    raise RuntimeError(f"Failed to open stage at {SCENE_PATH}")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def setup_stereo_baseline(baseline_m: float = 0.12):
    """Force stereo cameras to correct baseline."""
    left_path = "/World/StereoCameraRig/LeftCamera"
    right_path = "/World/StereoCameraRig/RightCamera"
    
    left_prim = stage.GetPrimAtPath(left_path)
    right_prim = stage.GetPrimAtPath(right_path)
    
    if not left_prim.IsValid() or not right_prim.IsValid():
        print("Warning: Could not find stereo cameras to set baseline!")
        return

    # Set translations (assuming X-axis separation)
    # Left at -baseline/2, Right at +baseline/2
    half_base = baseline_m / 2.0
    
    # Use UsdGeom.Xformable to set translate op
    left_xform = UsdGeom.Xformable(left_prim)
    right_xform = UsdGeom.Xformable(right_prim)
    
    # Get or create translate op
    # Try to find existing translate op
    left_op = None
    for op in left_xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            left_op = op
            break
    if not left_op:
        left_op = left_xform.AddTranslateOp()
        
    right_op = None
    for op in right_xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            right_op = op
            break
    if not right_op:
        right_op = right_xform.AddTranslateOp()
    
    left_op.Set(Gf.Vec3d(-half_base, 0, 0))
    right_op.Set(Gf.Vec3d(half_base, 0, 0))
    
    print(f"Set stereo baseline to {baseline_m*1000:.1f}mm")

    # Debug: Print world transforms
    # from pxr import UsdGeom  <-- Removed to avoid UnboundLocalError
    l_xform = UsdGeom.Xformable(left_prim)
    r_xform = UsdGeom.Xformable(right_prim)
    rig_prim = stage.GetPrimAtPath("/World/StereoCameraRig")
    rig_xform = UsdGeom.Xformable(rig_prim)
    
    print(f"Rig Scale: {rig_xform.ComputeLocalToWorldTransform(0).GetRow3(0)}") # Approximate scale check
    print(f"Left Local Pos: {left_op.Get()}")
    print(f"Right Local Pos: {right_op.Get()}")
    
    # Check Pantograph position
    pan_prim = stage.GetPrimAtPath("/World/Pantograph")
    if pan_prim.IsValid():
        pan_xform = UsdGeom.Xformable(pan_prim)
        print(f"Pantograph World Pos: {pan_xform.ComputeLocalToWorldTransform(0).ExtractTranslation()}")



def set_semantic_label(prim_path: str, label: str) -> None:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(f"Missing prim at {prim_path}")
    attr = prim.CreateAttribute("semantics:class", Sdf.ValueTypeNames.Token)
    attr.Set(label)


# Ensure baseline is correct before capturing
setup_stereo_baseline(0.12)

with rep.new_layer():
    set_semantic_label("/World/Pantograph", "pantograph")
    set_semantic_label("/World/Ground", "ground")
    set_semantic_label("/World/CatenaryWire", "catenary")

    # Create render products from the existing stereo cameras
    left_rp = rep.create.render_product(
        "/World/StereoCameraRig/LeftCamera", resolution=RESOLUTION
    )
    right_rp = rep.create.render_product(
        "/World/StereoCameraRig/RightCamera", resolution=RESOLUTION
    )

    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(
        output_dir=OUTPUT_DIR,
        rgb=True,
        distance_to_camera=True,
        semantic_segmentation=True,
    )
    writer.attach([left_rp, right_rp])

# Run a small capture
for i in range(NUM_FRAMES):
    rep.orchestrator.step()
    simulation_app.update()
    
    if i == 0:
        # Check camera positions after first step
        l_prim = stage.GetPrimAtPath("/World/StereoCameraRig/LeftCamera")
        r_prim = stage.GetPrimAtPath("/World/StereoCameraRig/RightCamera")
        l_xform = UsdGeom.Xformable(l_prim)
        r_xform = UsdGeom.Xformable(r_prim)
        l_pos = l_xform.ComputeLocalToWorldTransform(0).ExtractTranslation()
        r_pos = r_xform.ComputeLocalToWorldTransform(0).ExtractTranslation()
        print(f"Frame 0 Camera World Pos: L={l_pos}, R={r_pos}")
        dist = (l_pos - r_pos).GetLength()
        print(f"Frame 0 Baseline: {dist*1000:.1f}mm")

for _ in range(5):
    simulation_app.update()

print(f"Wrote outputs to: {OUTPUT_DIR}")
simulation_app.close()
