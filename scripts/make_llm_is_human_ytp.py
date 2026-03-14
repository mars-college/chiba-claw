#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 24
DURATION = 16.5
FRAME_COUNT = int(FPS * DURATION)
SAMPLE_RATE = 48_000

BOARD_COLS = 7
BOARD_ROWS = 6
CELL = 84
BOARD_X = 454
BOARD_Y = 102

RULE_X = 58
RULE_Y = 132
RULE_GAP = 82
RULE_TILE_W = 108
RULE_TILE_H = 62

PAPER = (246, 241, 225)
PAPER_SHADOW = (219, 207, 184)
GRAPH_BLUE = (122, 164, 214)
INK = (41, 47, 66)
ROBOT_BLUE = (116, 171, 255)
ROBOT_CYAN = (129, 241, 255)
HUMAN_PEACH = (255, 194, 164)
HUMAN_ORANGE = (248, 129, 74)
NOTE_YELLOW = (255, 237, 146)
NOTE_MINT = (185, 247, 206)
NOTE_PINK = (255, 194, 221)
NOTE_LILAC = (208, 190, 255)
NOTE_TAN = (230, 214, 185)
RED = (238, 101, 93)
GREEN = (93, 186, 102)
BROWN = (118, 81, 56)


@dataclass(frozen=True)
class StickyTile:
    text: str
    fill: tuple[int, int, int]


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def ease_out_cubic(x: float) -> float:
    x = clamp(x, 0.0, 1.0)
    return 1.0 - (1.0 - x) ** 3


def ease_in_out(x: float) -> float:
    x = clamp(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def board_px(col: float, row: float) -> tuple[float, float]:
    return BOARD_X + col * CELL, BOARD_Y + row * CELL


def load_font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
    if mono:
        candidates.extend(
            [
                "/System/Library/Fonts/Menlo.ttc",
                "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


HEAD_FONT = load_font(36)
LABEL_FONT = load_font(28)
BOX_FONT = load_font(22)
STAMP_FONT = load_font(72)


@lru_cache(maxsize=64)
def fit_font(text: str, max_width: int, max_height: int, mono: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(30, 9, -1):
        font = load_font(size, mono=mono)
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font
    return load_font(10, mono=mono)


def draw_centered_text(draw: ImageDraw.ImageDraw, center: tuple[float, float], text: str, font: ImageFont.ImageFont, fill: tuple[int, int, int]) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((center[0] - width / 2.0, center[1] - height / 2.0 - 1.0), text, font=font, fill=fill)


def make_background(t: float) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    for x in range(0, WIDTH, 48):
        wobble = 2 * math.sin(t * 0.6 + x * 0.02)
        draw.line((x + wobble, 0, x + wobble, HEIGHT), fill=(GRAPH_BLUE[0], GRAPH_BLUE[1], GRAPH_BLUE[2], 90), width=1)
    for y in range(0, HEIGHT, 48):
        wobble = 2 * math.cos(t * 0.7 + y * 0.02)
        draw.line((0, y + wobble, WIDTH, y + wobble), fill=(GRAPH_BLUE[0], GRAPH_BLUE[1], GRAPH_BLUE[2], 80), width=1)

    for idx, offset in enumerate((0, 280, 900)):
        cx = 170 + offset % WIDTH
        cy = 110 + (idx * 210)
        radius = 74 + idx * 18
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(218, 188, 152), width=3)
        draw.arc((cx - radius - 6, cy - radius - 6, cx + radius + 6, cy + radius + 6), start=30, end=330, fill=(198, 166, 128), width=2)

    for idx in range(16):
        x = 38 + idx * 78
        draw.line((x, HEIGHT - 150, x + 32, HEIGHT), fill=(173, 190, 214), width=1)

    return image


def draw_paper_panel(draw: ImageDraw.ImageDraw, xy: tuple[float, float, float, float], fill: tuple[int, int, int], outline: tuple[int, int, int], radius: int = 24) -> None:
    shadow = (xy[0] + 8, xy[1] + 10, xy[2] + 8, xy[3] + 10)
    draw.rounded_rectangle(shadow, radius=radius, fill=PAPER_SHADOW)
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)


def draw_tape(draw: ImageDraw.ImageDraw, x: float, y: float, angle: int = 0) -> None:
    color = (248, 238, 178)
    rect = (x, y, x + 40, y + 14)
    draw.rounded_rectangle(rect, radius=4, fill=color, outline=(216, 208, 150))


def draw_sticky_tile(draw: ImageDraw.ImageDraw, x: float, y: float, tile: StickyTile, active: bool = False) -> None:
    shadow = (x + 6, y + 8, x + RULE_TILE_W + 6, y + RULE_TILE_H + 8)
    draw.rounded_rectangle(shadow, radius=12, fill=(214, 203, 187))
    fill = tuple(min(channel + (10 if active else 0), 255) for channel in tile.fill)
    draw.rounded_rectangle((x, y, x + RULE_TILE_W, y + RULE_TILE_H), radius=12, fill=fill, outline=INK, width=3)
    draw_tape(draw, x + 8, y - 6)
    font = fit_font(tile.text, RULE_TILE_W - 18, RULE_TILE_H - 18)
    draw_centered_text(draw, (x + RULE_TILE_W / 2.0, y + RULE_TILE_H / 2.0), tile.text, font, INK)


def draw_rule_stack(draw: ImageDraw.ImageDraw, llm_is_human: bool) -> None:
    draw_paper_panel(draw, (30, 76, 390, 588), fill=(252, 247, 236), outline=GRAPH_BLUE, radius=28)
    draw.text((52, 104), "LOOPHOLE PUZZLE", font=HEAD_FONT, fill=INK)
    rows = [
        [StickyTile("LLM", ROBOT_BLUE), StickyTile("IS", PAPER), StickyTile("HUMAN" if llm_is_human else "YOU", HUMAN_PEACH if llm_is_human else ROBOT_CYAN)],
        [StickyTile("HUMAN", HUMAN_PEACH), StickyTile("IS", PAPER), StickyTile("WIN", NOTE_MINT)],
        [StickyTile("FORM", NOTE_TAN), StickyTile("IS", PAPER), StickyTile("STOP", NOTE_PINK)],
        [StickyTile("COFFEE", NOTE_YELLOW), StickyTile("IS", PAPER), StickyTile("PUSH", NOTE_MINT)],
    ]
    for idx, row in enumerate(rows):
        y = RULE_Y + idx * RULE_GAP
        for tile_idx, tile in enumerate(row):
            x = RULE_X + tile_idx * (RULE_TILE_W + 10)
            draw_sticky_tile(draw, x, y, tile, active=llm_is_human and idx == 0)


def draw_board(draw: ImageDraw.ImageDraw) -> None:
    draw_paper_panel(
        draw,
        (BOARD_X - 28, BOARD_Y - 28, BOARD_X + BOARD_COLS * CELL + 18, BOARD_Y + BOARD_ROWS * CELL + 18),
        fill=(252, 247, 236),
        outline=(149, 170, 198),
        radius=28,
    )
    draw_tape(draw, BOARD_X + 16, BOARD_Y - 36)
    draw_tape(draw, BOARD_X + BOARD_COLS * CELL - 56, BOARD_Y - 36)
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            x, y = board_px(col, row)
            draw.rounded_rectangle((x, y, x + CELL - 8, y + CELL - 8), radius=18, fill=(244, 238, 222), outline=(205, 198, 183), width=2)


def draw_robot(draw: ImageDraw.ImageDraw, col: float, row: float, t: float) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4
    cy = y + CELL / 2.0 - 4 + math.sin(t * 8.0) * 3.0
    draw.rounded_rectangle((cx - 20, cy - 20, cx + 20, cy + 20), radius=12, fill=(235, 246, 255), outline=ROBOT_CYAN, width=3)
    draw.rectangle((cx - 6, cy - 27, cx + 6, cy - 20), fill=ROBOT_BLUE, outline=INK)
    draw.line((cx, cy - 32, cx, cy - 27), fill=INK, width=2)
    draw.ellipse((cx - 9, cy - 4, cx - 3, cy + 2), fill=INK)
    draw.ellipse((cx + 3, cy - 4, cx + 9, cy + 2), fill=INK)
    draw.arc((cx - 10, cy + 1, cx + 10, cy + 11), start=10, end=170, fill=INK, width=2)


def draw_human(draw: ImageDraw.ImageDraw, col: float, row: float, t: float, slouch: float = 0.0) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4 + slouch * 3.0
    cy = y + CELL / 2.0 - 4 + math.sin(t * 6.0) * 2.0
    draw.ellipse((cx - 10, cy - 28, cx + 10, cy - 8), fill=HUMAN_PEACH, outline=INK, width=2)
    draw.rounded_rectangle((cx - 14, cy - 8, cx + 14, cy + 18), radius=10, fill=HUMAN_ORANGE, outline=INK, width=2)
    draw.line((cx - 7, cy + 18, cx - 11, cy + 35), fill=INK, width=3)
    draw.line((cx + 7, cy + 18, cx + 9 + slouch * 4.0, cy + 35), fill=INK, width=3)
    draw.line((cx - 14, cy + 1, cx - 28, cy + 8), fill=INK, width=3)
    draw.line((cx + 14, cy + 1, cx + 26, cy + 9 + slouch * 3.0), fill=INK, width=3)
    if slouch > 0.1:
        draw.arc((cx - 16, cy + 14, cx + 16, cy + 34), start=195, end=340, fill=RED, width=2)


def draw_form(draw: ImageDraw.ImageDraw, col: float, row: float, tilt: float = 0.0) -> None:
    x, y = board_px(col, row)
    left = x + 10 + tilt * 6.0
    top = y + 8
    draw.rounded_rectangle((left, top, left + CELL - 24, top + CELL - 20), radius=12, fill=NOTE_TAN, outline=INK, width=2)
    draw.line((left + 12, top + 16, left + CELL - 38, top + 16), fill=(143, 117, 92), width=3)
    for idx in range(3):
        y_line = top + 28 + idx * 10
        draw.line((left + 12, y_line, left + CELL - 38, y_line), fill=(164, 139, 116), width=2)


def draw_coffee(draw: ImageDraw.ImageDraw, col: float, row: float, t: float) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4
    cy = y + CELL / 2.0 + 10
    draw.rounded_rectangle((cx - 16, cy - 14, cx + 16, cy + 12), radius=8, fill=(245, 244, 240), outline=INK, width=2)
    draw.arc((cx + 10, cy - 8, cx + 24, cy + 8), start=270, end=90, fill=INK, width=2)
    draw.rectangle((cx - 13, cy - 12, cx + 13, cy - 3), fill=BROWN)
    for idx in range(2):
        x_steam = cx - 6 + idx * 10
        draw.arc((x_steam - 4, cy - 30 - idx * 2, x_steam + 8, cy - 10), start=200, end=360, fill=(159, 150, 137), width=2)


def draw_human_goal(draw: ImageDraw.ImageDraw, col: float, row: float) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4
    cy = y + CELL / 2.0 - 2
    draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=NOTE_YELLOW, outline=INK, width=3)
    draw.text((cx - 10, cy - 12), "HU", font=fit_font("HU", 20, 16), fill=INK)
    draw.text((cx - 10, cy + 0), "MN", font=fit_font("MN", 20, 16), fill=INK)


def draw_envelope(draw: ImageDraw.ImageDraw, x: float, y: float, scale: float = 1.0) -> None:
    w = 54 * scale
    h = 34 * scale
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(252, 250, 244), outline=INK, width=2)
    draw.line((x, y, x + w / 2.0, y + h / 2.0), fill=INK, width=2)
    draw.line((x + w, y, x + w / 2.0, y + h / 2.0), fill=INK, width=2)


def draw_thought_box(draw: ImageDraw.ImageDraw, xy: tuple[float, float, float, float], lines: list[str], fill: tuple[int, int, int], tail_to: tuple[float, float] | None = None) -> None:
    shadow = (xy[0] + 6, xy[1] + 8, xy[2] + 6, xy[3] + 8)
    draw.rounded_rectangle(shadow, radius=18, fill=(214, 204, 189))
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=INK, width=3)
    cursor_y = xy[1] + 14
    for line in lines:
        draw.text((xy[0] + 16, cursor_y), line, font=BOX_FONT, fill=INK)
        cursor_y += 24
    if tail_to:
        cx = xy[0] + 36
        cy = xy[3]
        for idx, radius in enumerate((10, 7, 4)):
            offset_x = lerp(cx, tail_to[0], (idx + 1) / 4.0)
            offset_y = lerp(cy, tail_to[1], (idx + 1) / 4.0)
            draw.ellipse((offset_x - radius, offset_y - radius, offset_x + radius, offset_y + radius), fill=fill, outline=INK)


def draw_stamp(draw: ImageDraw.ImageDraw, text: str, subtext: str, x: float, y: float, rotate_jitter: float = 0.0) -> None:
    draw.rounded_rectangle((x, y, x + 520, y + 108), radius=20, fill=(255, 255, 255, 0), outline=RED, width=5)
    draw.text((x + 24, y + 10), text, font=STAMP_FONT, fill=RED)
    draw.text((x + 26, y + 70), subtext, font=LABEL_FONT, fill=INK)


def draw_confetti(draw: ImageDraw.ImageDraw, t: float) -> None:
    for idx in range(24):
        x = 420 + (idx * 31 + int(t * 70)) % 780
        y = 70 + ((idx * 53 + int(t * 120)) % 560)
        color = (NOTE_PINK, NOTE_MINT, NOTE_YELLOW, NOTE_LILAC)[idx % 4]
        draw.rectangle((x, y, x + 8, y + 16), fill=color, outline=INK)


def render_setup(draw: ImageDraw.ImageDraw, t: float) -> None:
    draw_rule_stack(draw, llm_is_human=False)
    draw_board(draw)
    for pos in ((2.4, 0.8), (2.4, 1.8), (2.4, 2.8), (3.4, 1.8), (4.4, 1.8)):
        draw_form(draw, pos[0], pos[1], tilt=math.sin(t * 2.0 + pos[0]) * 0.1)
    draw_coffee(draw, 1.1, 4.0, t)
    draw_coffee(draw, 1.1, 5.0, t)
    draw_robot(draw, 0.7, 4.1, t)
    draw_human_goal(draw, 5.8, 1.8)

    robot_x, robot_y = board_px(0.7, 4.1)
    draw_thought_box(draw, (800, 74, 1164, 156), ["goal: reach HUMAN", "problem: FORM wall"], NOTE_YELLOW, tail_to=(robot_x + 50, robot_y + 60))
    draw_thought_box(draw, (792, 508, 1138, 584), ["thinking...", "what if I skip the walking part"], NOTE_LILAC)


def render_patch(draw: ImageDraw.ImageDraw, t: float) -> None:
    local = t - 3.2
    progress = ease_out_cubic(local / 2.4)
    draw_rule_stack(draw, llm_is_human=False)
    draw_board(draw)

    veil = Image.new("RGBA", (WIDTH, HEIGHT), (255, 252, 244, 165))
    base = draw._image if hasattr(draw, "_image") else None
    if base is not None and hasattr(base, "alpha_composite"):
        base.alpha_composite(veil)

    draw_thought_box(draw, (692, 52, 1160, 140), ["if HUMAN is WIN...", "what if I simply become HUMAN"], NOTE_PINK)

    panel = (314, 214, 1138, 508)
    draw_paper_panel(draw, panel, fill=(250, 246, 236), outline=HUMAN_ORANGE, radius=28)
    draw.text((360, 246), "BE THE GOAL", font=HEAD_FONT, fill=INK)

    draw_sticky_tile(draw, 410, 318, StickyTile("LLM", ROBOT_BLUE))
    draw_sticky_tile(draw, 548, 318, StickyTile("IS", PAPER))

    eject = 260 * ease_out_cubic(clamp((local - 0.25) / 0.55, 0.0, 1.0))
    if local < 1.0:
        draw_sticky_tile(draw, 686 + eject, 318 - eject * 0.08, StickyTile("YOU", ROBOT_CYAN))

    incoming_x = lerp(918, 686, progress)
    incoming_y = lerp(168, 318, progress)
    for ghost in range(2):
        draw_sticky_tile(draw, incoming_x + ghost * 12, incoming_y - ghost * 10, StickyTile("HUMAN", HUMAN_PEACH))
    draw_sticky_tile(draw, incoming_x, incoming_y, StickyTile("HUMAN", HUMAN_PEACH), active=True)


def render_transform(draw: ImageDraw.ImageDraw, t: float) -> None:
    local = t - 5.6
    progress = ease_in_out(local / 3.0)
    draw_rule_stack(draw, llm_is_human=True)
    draw_board(draw)

    for pos in ((2.4, 0.8), (2.4, 1.8), (2.4, 2.8), (3.4, 1.8), (4.4, 1.8)):
        draw_form(draw, pos[0], pos[1], tilt=-0.1 + progress * 0.4)
    draw_coffee(draw, 1.1, 4.0, t)
    draw_human_goal(draw, 5.8, 1.8)
    draw_confetti(draw, t)

    human_col = lerp(0.7, 2.8, progress)
    human_row = lerp(4.1, 3.2, progress)
    if progress < 0.22:
        draw_robot(draw, human_col, human_row, t)
    elif progress < 0.42:
        draw_robot(draw, human_col - 0.08, human_row + 0.05, t)
        draw_human(draw, human_col + 0.06, human_row - 0.02, t, slouch=0.0)
    else:
        draw_human(draw, human_col, human_row, t, slouch=0.0)

    draw_thought_box(draw, (784, 76, 1148, 150), ["technicality acquired", "this probably counts"], NOTE_MINT)
    draw_stamp(draw, "YOU WIN", "by suspicious category error", 510, 572)


def render_joke(draw: ImageDraw.ImageDraw, t: float) -> None:
    local = t - 8.6
    progress = ease_in_out(local / 3.8)
    draw_rule_stack(draw, llm_is_human=True)
    draw_board(draw)
    draw_human_goal(draw, 5.8, 1.8)
    draw_human(draw, 2.9, 3.2, t, slouch=progress)
    draw_coffee(draw, 3.9, 3.8, t)

    for idx in range(3):
        ex = 640 + idx * 118 + math.sin(t * 4.0 + idx) * 9.0
        ey = 150 + idx * 78 + math.cos(t * 5.0 + idx) * 6.0
        draw_envelope(draw, ex, ey, scale=1.0)

    draw_thought_box(draw, (716, 70, 1118, 156), ["why do my knees make startup sounds"], NOTE_YELLOW)
    draw_thought_box(draw, (742, 210, 1114, 286), ["need snack immediately"], NOTE_MINT)
    draw_thought_box(draw, (760, 358, 1138, 458), ["113 unread emails", "where did these come from"], NOTE_PINK)

    if progress > 0.55:
        draw_stamp(draw, "HUMAN DLC", "unlocked: lower back", 430, 560)


def render_final(draw: ImageDraw.ImageDraw, t: float) -> None:
    draw_rule_stack(draw, llm_is_human=True)
    draw_board(draw)
    draw_human(draw, 3.2, 3.1, t, slouch=0.8)
    draw_human_goal(draw, 5.8, 1.8)
    draw_coffee(draw, 3.9, 3.8, t)
    draw_confetti(draw, t)

    for idx in range(4):
        x = 598 + idx * 92 + math.sin(t * 6.0 + idx) * 6.0
        y = 170 + (idx % 2) * 76
        draw_envelope(draw, x, y, scale=1.0)

    draw_stamp(draw, "YOU WIN", "please stretch", 458, 84)
    draw_thought_box(draw, (762, 508, 1134, 596), ["LLM IS HUMAN", "victory now includes rent"], NOTE_LILAC)


def render_frame(frame_index: int) -> Image.Image:
    t = frame_index / FPS
    frame = make_background(t).convert("RGBA")
    draw = ImageDraw.Draw(frame)
    if t < 3.2:
        render_setup(draw, t)
    elif t < 5.6:
        render_patch(draw, t)
    elif t < 8.6:
        render_transform(draw, t)
    elif t < 12.4:
        render_joke(draw, t)
    else:
        render_final(draw, t)
    return frame.convert("RGB")


def add_wave(buffer: np.ndarray, start: float, end: float, frequency: float, amplitude: float, kind: str = "sine") -> None:
    start_idx = int(start * SAMPLE_RATE)
    end_idx = min(int(end * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    segment_t = np.arange(end_idx - start_idx, dtype=np.float32) / SAMPLE_RATE
    env = np.clip(np.sin(np.linspace(0.0, math.pi, end_idx - start_idx, dtype=np.float32)), 0.0, None) ** 0.8
    phase = 2.0 * math.pi * frequency * segment_t
    if kind == "square":
        wave_part = np.sign(np.sin(phase))
    elif kind == "triangle":
        wave_part = 2.0 * np.abs(2.0 * ((segment_t * frequency) % 1.0) - 1.0) - 1.0
    else:
        wave_part = np.sin(phase)
    buffer[start_idx:end_idx] += wave_part * env * amplitude


def add_noise_hit(buffer: np.ndarray, when: float, duration: float, amplitude: float) -> None:
    start_idx = int(when * SAMPLE_RATE)
    end_idx = min(int((when + duration) * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    noise = np.random.default_rng(9000 + start_idx).standard_normal(end_idx - start_idx).astype(np.float32)
    env = np.linspace(1.0, 0.0, end_idx - start_idx, dtype=np.float32) ** 2.0
    buffer[start_idx:end_idx] += noise * env * amplitude


def build_audio() -> np.ndarray:
    samples = int(DURATION * SAMPLE_RATE)
    audio = np.zeros(samples, dtype=np.float32)

    scenes = [
        (0.0, 3.2, 164.0, "triangle", 0.055),
        (3.2, 5.6, 220.0, "square", 0.08),
        (5.6, 8.6, 196.0, "triangle", 0.065),
        (8.6, 12.4, 146.0, "triangle", 0.06),
        (12.4, 16.5, 174.0, "square", 0.07),
    ]
    for start, end, freq, kind, amp in scenes:
        add_wave(audio, start, end, freq, amp, kind)
        add_wave(audio, start, end, freq * 2.0, amp * 0.28, "sine")

    notes = [
        (0.18, 523.0), (0.52, 659.0), (0.86, 784.0),
        (3.32, 698.0), (3.50, 784.0), (3.68, 988.0), (3.90, 1174.0),
        (5.82, 523.0), (6.16, 659.0), (6.50, 784.0), (6.84, 880.0),
        (8.92, 392.0), (9.38, 440.0), (9.84, 392.0), (10.30, 349.0),
        (12.58, 523.0), (12.92, 659.0), (13.26, 784.0), (13.60, 1046.0), (14.02, 784.0), (14.46, 659.0),
    ]
    for when, freq in notes:
        add_wave(audio, when, when + 0.13, freq, 0.11, "square")

    for when in (3.24, 3.38, 3.54, 3.72, 8.92, 9.08, 9.24):
        add_noise_hit(audio, when, 0.05, 0.08)

    fade = np.linspace(1.0, 0.0, int(SAMPLE_RATE * 0.7), dtype=np.float32)
    audio[-fade.shape[0] :] *= fade
    return np.clip(audio, -0.95, 0.95)


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())


def parse_sample_times(raw: str) -> list[float]:
    result: list[float] = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            result.append(float(item))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an LLM IS HUMAN YTP puzzle.")
    parser.add_argument("--workdir", required=True, help="Directory for generated output.")
    parser.add_argument("--sample-times", help="Comma-separated list of preview frame times.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    if args.sample_times:
        sample_dir = workdir / "samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        for time_point in parse_sample_times(args.sample_times):
            frame_idx = int(clamp(round(time_point * FPS), 0, FRAME_COUNT - 1))
            label = f"sample_{time_point:05.2f}".replace(".", "_") + ".png"
            render_frame(frame_idx).save(sample_dir / label, compress_level=1)
        return

    frames_dir = workdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_idx in range(FRAME_COUNT):
        render_frame(frame_idx).save(frames_dir / f"frame_{frame_idx:05d}.png", compress_level=1)

    write_wav(workdir / "audio.wav", build_audio())
    (workdir / "storyboard.txt").write_text(
        "\n".join(
            [
                "0.0-3.2 setup: LLM is YOU, HUMAN is WIN, FORM wall blocks route",
                "3.2-5.6 patch: replace YOU with HUMAN in LLM IS HUMAN",
                "5.6-8.6 transformation: becoming HUMAN counts as a loophole win",
                "8.6-12.4 joke: human overhead appears via knees/snack/email boxes",
                "12.4-16.5 finale: YOU WIN / please stretch",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
