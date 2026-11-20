"""Generate reference images, two walkthrough videos and a site photo (offline, synthetic)."""

import random
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / 'data'
(OUT / 'reference').mkdir(parents=True, exist_ok=True)
(OUT / 'walkthrough').mkdir(parents=True, exist_ok=True)
PALETTES = {
    'C-101': [(30, 70, 190), (50, 100, 220), (240, 240, 235)],  # cobalt window
    'C-102': [(235, 160, 30), (245, 190, 60), (200, 120, 20)],  # amber door panel
    'C-103': [(30, 150, 80), (60, 180, 100), (20, 110, 60)],  # emerald transom
    'C-104': [(150, 40, 170), (120, 30, 150), (190, 90, 200)],  # violet rose window
}


def window(cid: str, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    img = Image.new('RGB', (640, 480), (10, 10, 10))
    d = ImageDraw.Draw(img)
    for gx in range(8):
        for gy in range(6):
            x0, y0 = gx * 80, gy * 80
            d.rectangle([x0 + 4, y0 + 4, x0 + 76, y0 + 76], fill=rnd.choice(PALETTES[cid]))
    return img


def video(path: Path, color, seconds: float = 5.0, fps: int = 10) -> None:
    c = av.open(str(path), 'w')
    s = c.add_stream('libx264', rate=fps)
    s.width, s.height, s.pix_fmt = 320, 240, 'yuv420p'
    n = int(seconds * fps)
    for i in range(n):
        level = 0.35 + 0.65 * (i / n)
        arr = np.zeros((240, 320, 3), dtype=np.uint8)
        arr[:] = [int(v * level) for v in color]
        arr[:, (i * 6) % 320 : (i * 6) % 320 + 8] = 255  # a light slat sweeping across
        f = av.VideoFrame.from_ndarray(arr, format='rgb24')
        for p in s.encode(f):
            c.mux(p)
    for p in s.encode():
        c.mux(p)
    c.close()


for i, cid in enumerate(PALETTES):
    window(cid, i).save(OUT / 'reference' / f'{cid}.png')
for cid in ('C-101', 'C-102', 'C-103'):  # C-104 has no walkthrough on purpose
    video(OUT / 'walkthrough' / f'{cid}.mp4', PALETTES[cid][0], seconds=5.0 if cid != 'C-103' else 1.2)
Image.new('RGB', (640, 480), (120, 130, 140)).save(OUT / 'site-photo.png')
print('data ready in', OUT)
