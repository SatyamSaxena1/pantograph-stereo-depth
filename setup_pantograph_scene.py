#!/usr/bin/env python3
# Setup pantograph scene with stereo camera rig for metric depth capture

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False, "width": 1920, "height": 1080})

import omni.kit.commands
from pxr import Usd, UsdGeom, Gf, Sdf
import numpy as np

# Paths
USD_PATH = r"D:\\isaac-sim-standalone-5.1.0-windows-x86_64\\isaac-sim-standalone-5.1.0-windows-x86_64\\poly_converted.usd"
OUTPUT_SCENE = r"D:\\isaac-sim-standalone-5.1.0-windows-x86_64\\isaac-sim-standalone-5.1.0-windows-x86_64\\pantograph_stereo_scene.usd"

# Stereo camera config (matching your ZED-like specs)
BASELINE_M = 0.12  # 120mm baseline (adjust if you have exact spec)
CAMERA_DISTANCE_M = 1.5  # 1.5m from pantograph (within your 1-2m range)
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
HFOV_DEG = 90  # Approximate for ZED

# Create new stage
stage = omni.usd.get_context().new_stage()
stage = omni.usd.get_context().get_stage()

# Set stage units to meters, Z-up
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

print("Creating scene...")

# 1. Create root Xform for the pantograph
panto_root = UsdGeom.Xform.Define(stage, "/World/Pantograph")
# GLB was Y-up, Isaac Sim is Z-up: rotate +90 around X to stand it upright
panto_root.AddRotateXYZOp().Set(Gf.Vec3d(90, 0, 0))
panto_root.AddTranslateOp().Set(Gf.Vec3d(0, 0, 1.5))  # Lift so contact head is ~1.5m up

# Reference the converted USD
panto_root.GetPrim().GetReferences().AddReference(USD_PATH)

print("Pantograph placed upright with contact head raised")

# 2. Create stereo camera rig
rig_root = UsdGeom.Xform.Define(stage, "/World/StereoCameraRig")
# Position rig looking at pantograph from CAMERA_DISTANCE_M away, at same height as contact head
rig_root.AddTranslateOp().Set(Gf.Vec3d(0, -CAMERA_DISTANCE_M, 1.5))
# Rotate to look toward +Y (toward pantograph)
rig_root.AddRotateXYZOp().Set(Gf.Vec3d(90, 0, 0))

# Compute focal length from HFOV
focal_length_mm = (IMAGE_WIDTH / 2) / np.tan(np.radians(HFOV_DEG / 2))
focal_length_mm = focal_length_mm * 0.0036  # Convert px to mm assuming 3.6um pixel pitch

# Left camera
left_cam = UsdGeom.Camera.Define(stage, "/World/StereoCameraRig/LeftCamera")
left_cam.AddTranslateOp().Set(Gf.Vec3d(-BASELINE_M / 2, 0, 0))
left_cam.GetHorizontalApertureAttr().Set(6.912)  # 1920 * 3.6um in mm
left_cam.GetVerticalApertureAttr().Set(3.888)    # 1080 * 3.6um in mm
left_cam.GetFocalLengthAttr().Set(3.5)           # ~90 deg HFOV
left_cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 100.0))

# Right camera
right_cam = UsdGeom.Camera.Define(stage, "/World/StereoCameraRig/RightCamera")
right_cam.AddTranslateOp().Set(Gf.Vec3d(BASELINE_M / 2, 0, 0))
right_cam.GetHorizontalApertureAttr().Set(6.912)
right_cam.GetVerticalApertureAttr().Set(3.888)
right_cam.GetFocalLengthAttr().Set(3.5)
right_cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 100.0))

print(f"Stereo rig placed: baseline={BASELINE_M*1000:.0f}mm, distance={CAMERA_DISTANCE_M}m")

# 3. Add ground plane at Z=0
ground = UsdGeom.Mesh.Define(stage, "/World/Ground")
ground.CreatePointsAttr([(-10, -10, 0), (10, -10, 0), (10, 10, 0), (-10, 10, 0)])
ground.CreateFaceVertexCountsAttr([4])
ground.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
ground.CreateNormalsAttr([(0, 0, 1)])

# 4. Add dome light for even illumination
light = UsdGeom.Xform.Define(stage, "/World/DomeLight")
dome_light = stage.DefinePrim("/World/DomeLight/Dome", "DomeLight")
dome_light.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1000.0)

# 5. Add a simple catenary wire above pantograph (approximation)
# Pantograph contact head is at ~1.5m, wire slightly above
wire_points = []
for i in range(21):
    x = (i - 10) * 0.3  # -3m to +3m
    z = 1.8 + 0.02 * (x ** 2)  # Slight sag, base at 1.8m (0.3m above contact head)
    wire_points.append((x, 0, z))

wire = UsdGeom.BasisCurves.Define(stage, "/World/CatenaryWire")
wire.CreatePointsAttr(wire_points)
wire.CreateCurveVertexCountsAttr([21])
wire.CreateTypeAttr("cubic")
wire.CreateBasisAttr("bspline")
wire.CreateWidthsAttr([0.012] * 21)  # 12mm diameter wire

print("Catenary wire added")

# Save scene
stage.GetRootLayer().Export(OUTPUT_SCENE)
print(f"\nScene saved to: {OUTPUT_SCENE}")

# Print disparity range for your stereo matcher
fx_px = 3.5 / (6.912 / IMAGE_WIDTH)  # focal length in pixels
d_near = (fx_px * BASELINE_M) / 1.0  # disparity at 1m
d_far = (fx_px * BASELINE_M) / 2.0   # disparity at 2m
print(f"\n=== STEREO MATCHER SETTINGS ===")
print(f"Focal length: {fx_px:.1f} px")
print(f"Baseline: {BASELINE_M*1000:.0f} mm")
print(f"Disparity at 1m: {d_near:.1f} px")
print(f"Disparity at 2m: {d_far:.1f} px")
print(f"Recommended disparity range: {int(d_far)-10} to {int(d_near)+20} px")

print("\nScene ready. Opening viewer...")

# Keep app open for viewing
while simulation_app.is_running():
    simulation_app.update()

simulation_app.close()
