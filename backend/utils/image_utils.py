"""
Image utilities for Ocean Waste Detection System.
"""
import base64
import cv2
import numpy as np
from pathlib import Path


def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_comparison_image(clean_path: str, polluted_annotated: np.ndarray) -> np.ndarray:
    """
    Creates a side-by-side comparison between a clean ocean image
    and the annotated polluted image.
    """
    clean = cv2.imread(clean_path)
    if clean is None:
        clean = np.zeros_like(polluted_annotated)

    TARGET_H = 480
    TARGET_W = 640

    def resize(img):
        return cv2.resize(img, (TARGET_W, TARGET_H))

    clean_r = resize(clean)
    polluted_r = resize(polluted_annotated)

    # Add labels
    label_bar_h = 40
    label_bar_c = np.zeros((label_bar_h, TARGET_W, 3), dtype=np.uint8)
    label_bar_p = np.zeros((label_bar_h, TARGET_W, 3), dtype=np.uint8)
    label_bar_c[:] = (30, 140, 30)
    label_bar_p[:] = (30, 30, 180)

    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(label_bar_c, "CLEAN OCEAN", (TARGET_W // 2 - 90, 28),
                font, 0.75, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(label_bar_p, "WASTE DETECTED", (TARGET_W // 2 - 110, 28),
                font, 0.75, (255, 255, 255), 1, cv2.LINE_AA)

    left = np.vstack([label_bar_c, clean_r])
    right = np.vstack([label_bar_p, polluted_r])

    divider = np.full((TARGET_H + label_bar_h, 6, 3), 255, dtype=np.uint8)
    comparison = np.hstack([left, divider, right])
    return comparison


def generate_heatmap_overlay(image_path: str) -> np.ndarray:
    """Apply a JET colormap overlay to simulate thermal detection."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    eq = cv2.equalizeHist(gray)
    colormap = cv2.applyColorMap(eq, cv2.COLORMAP_JET)
    return cv2.addWeighted(img, 0.5, colormap, 0.5, 0)
