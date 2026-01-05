# Pantograph Stereo Depth

Scripts for NVIDIA Isaac Sim to build a pantograph scene, capture stereo RGB/depth/semantic data, and run an OpenCV StereoSGBM depth pipeline with evaluation against simulator ground truth.

## Components
- setup_pantograph_scene.py: builds a pantograph stage with stereo rig, dome light, and catenary wire; writes pantograph_stereo_scene.usd.
- capture_pantograph_data.py: headless Replicator capture of RGB, distance_to_camera, and semantic_segmentation from the stereo cameras.
- stereo_pipeline.py: OpenCV StereoSGBM with optional WLS filtering and temporal smoothing; exports disparity/depth/point clouds and computes metrics vs ground truth.

## Techniques & Approach
- Scene authoring: constructs a metric stage (meters, Z-up) with a pantograph asset, stereo rig (120 mm baseline, ~90 deg HFOV), ground plane, dome light, and catenary wire to match expected geometry and lighting.
- Baseline enforcement: sets camera translate ops each run to guarantee the intended stereo baseline even if scene edits drift.
- Replicator capture: uses headless RayTracedLighting with BasicWriter to export RGB, distance_to_camera (GT depth), and semantic_segmentation for both stereo views at 1920x1080.
- Depth algorithm: StereoSGBM tuned for thin structures (blockSize 3, dense matching, HH mode) with optional ximgproc WLS filtering for cleaner edges.
- Temporal smoothing: exponential moving average on depth to reduce flicker across frames for downstream tracking/point-cloud stability.
- Calibration assumptions: uses ~972 px focal length derived from HFOV and pixel pitch; disparity bounds (48-144 px) cover ~0.7-3 m working distance (1-2 m target).
- Evaluation: compares estimated depth to simulator GT, reporting MAE, RMSE, abs_rel, and delta thresholds (1.25^k); saves per-frame metrics when GT is present.

## Requirements
- NVIDIA Isaac Sim 5.1 environment (for scene authoring and captures).
- Python 3.11 (Isaac Sim ships a matching python).
- Python packages: numpy, opencv-contrib-python.
- Assets: pantograph USD and supporting geometry; update the paths in the scripts to point at your local assets.

## Usage
1) Scene authoring: run `python setup_pantograph_scene.py` inside the Isaac Sim python environment. Adjust USD_PATH and OUTPUT_SCENE as needed.
2) Capture: run `python capture_pantograph_data.py` to write RGB, distance_to_camera, and semantic_segmentation to captures/. Adjust SCENE_PATH, OUTPUT_DIR, NUM_FRAMES, and RESOLUTION for your setup.
3) Depth pipeline: run `python stereo_pipeline.py --capture-dir captures/Replicator_01 --output-dir stereo_output --evaluate --visualize --temporal-smoothing`.

The depth pipeline saves disparity and depth visualizations plus depth .npy files. Evaluation uses distance_to_camera_*.npy from the Replicator BasicWriter when present.

## Notes
- Repository excludes simulator binaries, generated captures, and large assets.
- Install opencv-contrib-python if you want WLS filtering.
