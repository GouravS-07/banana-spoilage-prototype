"""
Shared Feature Extraction for Banana Ripeness Classification.
Extracts 12 explainable HSV color distribution and morphological dark-spot features
with strict mathematical conversion to degrees and consistent foreground masking.
Used identically across training in vision_evaluation/ and inference in app/.
"""

from typing import Union
from pathlib import Path
import numpy as np
from PIL import Image

FEATURE_NAMES = [
    "mean_h", "std_h",
    "mean_s", "std_s",
    "mean_v", "std_v",
    "green_ratio", "yellow_ratio", "brown_ratio",
    "dark_spot_ratio", "bright_ratio", "green_to_yellow"
]

def extract_features_from_image(img_input: Union[str, Path, Image.Image]) -> np.ndarray:
    """
    Extracts 12 explainable color and morphological features from an RGB image:
    1. mean_h: Mean Hue on foreground peel in degrees [0, 360)
    2. std_h: Standard deviation of Hue in degrees
    3. mean_s: Mean Saturation on foreground peel [0, 1]
    4. std_s: Standard deviation of Saturation
    5. mean_v: Mean Value (brightness) on foreground peel [0, 1]
    6. std_v: Standard deviation of Value
    7. green_ratio: Proportion of peel pixels with 60° <= Hue <= 140° (unripe chlorophyll)
    8. yellow_ratio: Proportion of peel pixels with 25° <= Hue < 60° (ripe carotenoids)
    9. brown_ratio: Proportion of peel pixels with Hue < 25° or Hue >= 330°
    10. dark_spot_ratio: Proportion of peel pixels with Value < 0.35 (senescent sugar spotting)
    11. bright_ratio: Proportion with Value > 0.85 (specular highlight)
    12. green_to_yellow: Ratio of green to yellow area
    """
    if isinstance(img_input, (str, Path)):
        img = Image.open(str(img_input)).convert("RGB")
    elif isinstance(img_input, Image.Image):
        img = img_input.convert("RGB")
    else:
        raise ValueError(f"Unsupported image input type: {type(img_input)}")

    # Ensure array is float32 normalized to [0, 1]
    arr = np.array(img, dtype=np.float32) / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    df = mx - mn
    
    # Value (brightness) in [0, 1]
    v = mx
    
    # Saturation in [0, 1]
    s = np.zeros_like(mx)
    mask_nz = (mx > 0)
    s[mask_nz] = df[mask_nz] / mx[mask_nz]
    
    # Hue strictly in degrees [0, 360)
    h = np.zeros_like(mx)
    rc = (mx - r) / (df + 1e-7)
    gc = (mx - g) / (df + 1e-7)
    bc = (mx - b) / (df + 1e-7)
    
    mask_r = (r == mx) & (df > 0)
    mask_g = (g == mx) & (df > 0)
    mask_b = (b == mx) & (df > 0)
    
    h[mask_r] = (bc[mask_r] - gc[mask_r]) * 60.0
    h[mask_g] = (2.0 + rc[mask_g] - bc[mask_g]) * 60.0
    h[mask_b] = (4.0 + gc[mask_b] - rc[mask_b]) * 60.0
    h = h % 360.0

    # Foreground segmentation: filter plain studio background (v > 0.88 and s < 0.15)
    fg = ~((v > 0.88) & (s < 0.15))
    # Fallback to entire image if background mask eliminates nearly everything
    if np.sum(fg) < 50:
        fg = np.ones_like(v, dtype=bool)
        
    h_fg = h[fg]
    s_fg = s[fg]
    v_fg = v[fg]
    
    # Feature computations
    mean_h = float(np.mean(h_fg))
    std_h = float(np.std(h_fg))
    mean_s = float(np.mean(s_fg))
    std_s = float(np.std(s_fg))
    mean_v = float(np.mean(v_fg))
    std_v = float(np.std(v_fg))
    
    green_ratio = float(np.mean((h_fg >= 60.0) & (h_fg <= 140.0)))
    yellow_ratio = float(np.mean((h_fg >= 25.0) & (h_fg < 60.0)))
    brown_ratio = float(np.mean((h_fg < 25.0) | (h_fg >= 330.0)))
    dark_spot_ratio = float(np.mean(v_fg < 0.35))
    bright_ratio = float(np.mean(v_fg > 0.85))
    green_to_yellow = float(green_ratio / (yellow_ratio + 1e-5))
    
    return np.array([
        mean_h, std_h,
        mean_s, std_s,
        mean_v, std_v,
        green_ratio, yellow_ratio, brown_ratio,
        dark_spot_ratio, bright_ratio, green_to_yellow
    ], dtype=np.float32)
