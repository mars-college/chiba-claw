#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 24
DURATION = 18.0
FRAME_COUNT = int(FPS * DURATION)
SAMPLE_RATE = 48_000

BOARD_COLS = 10
BOARD_ROWS = 7
CELL = 74
BOARD_X = 470
BOARD_Y = 96

SIDEBAR_X = 52
SIDEBAR_Y = 120
RULE_ROW_GAP = 78
RULE_TILE_W = 92
RULE_TILE_H = 58

BG_TOP = np.array((6, 11, 24), dtype=np.float32)
BG_BOTTOM = np.array((17, 7, 33), dtype=np.float32)
PANEL = (10, 16, 32)
PANEL_ALT = (14, 22, 42)
GRID = (19, 31, 55)
INK = (5, 8, 14)
WHITE = (246, 248, 255)
CYAN = (101, 245, 255)
TEAL = (53, 198, 209)
GREEN = (145, 255, 166)
LIME = (187, 255, 92)
YELLOW = (255, 226, 116)
AMBER = (255, 176, 65)
PINK = (255, 93, 214)
RED = (255, 89, 125)
BLUE = (122, 170, 255)
VIOLET = (188, 131, 255)


@dataclass(frozen=True)
class RuleTile:
    text: str
    fill: tuple[int, int, int]
    outline: tuple[int, int, int]


@dataclass(frozen=True)
class RuleRow:
    pieces: tuple[RuleTile, RuleTile, RuleTile]
    active: bool = False


@dataclass(frozen=True)
class Chip:
    label: str
    col: float
    row: float
    fill: tuple[int, int, int]
    outline: tuple[int, int, int]


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
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


HEAD_FONT = load_font(40)
LABEL_FONT = load_font(28)
HUD_FONT = load_font(24, mono=True)
RULE_FONT = load_font(30, mono=True)
BIG_FONT = load_font(72)


@lru_cache(maxsize=64)
def chip_font(text: str, max_width: int, max_height: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(30, 9, -1):
        font = load_font(size, mono=True)
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font
    return load_font(10, mono=True)


def glow_rect(
    base: Image.Image,
    xy: tuple[float, float, float, float],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    radius: int,
    width: int,
    glow: int = 18,
) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(xy, radius=radius, fill=fill + (230,), outline=outline + (255,), width=width)
    glow_layer = overlay.filter(ImageFilter.GaussianBlur(glow))
    base.alpha_composite(glow_layer)
    base.alpha_composite(overlay)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((center[0] - width / 2.0, center[1] - height / 2.0 - 1.0), text, font=font, fill=fill)


def make_background(t: float) -> Image.Image:
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        mix = y / max(HEIGHT - 1, 1)
        base = BG_TOP * (1.0 - mix) + BG_BOTTOM * mix
        wave = 16.0 * math.sin(mix * 9.5 + t * 1.9)
        row = np.clip(base + wave, 0.0, 255.0)
        canvas[y, :, :] = row.astype(np.uint8)

    image = Image.fromarray(canvas).convert("RGBA")
    draw = ImageDraw.Draw(image)

    for band in range(0, HEIGHT, 4):
        alpha = 16 if band % 8 == 0 else 8
        draw.rectangle((0, band, WIDTH, band + 1), fill=(255, 255, 255, alpha))

    for idx in range(18):
        x = int((idx * 91 + t * 70) % (WIDTH + 160)) - 80
        y = int(80 + 22 * math.sin(t * 0.8 + idx))
        draw.line((x, y, x + 80, HEIGHT - 20), fill=(37, 97, 138, 40), width=1)

    for idx, color in enumerate((CYAN, PINK, LIME)):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        radius = 150 + idx * 40
        cx = int(180 + idx * 370 + 80 * math.sin(t * (0.6 + idx * 0.1)))
        cy = int(120 + idx * 160 + 45 * math.cos(t * (0.8 + idx * 0.1)))
        glow_draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color + (36,))
        image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(44)))

    return image


def draw_panel(frame: Image.Image, xy: tuple[float, float, float, float], outline: tuple[int, int, int], radius: int = 24) -> None:
    glow_rect(frame, xy, PANEL, outline, radius=radius, width=3, glow=16)


def draw_rule_tile(frame: Image.Image, x: float, y: float, tile: RuleTile, active: bool = False, jumbo: bool = False) -> None:
    width = 120 if jumbo else RULE_TILE_W
    height = 70 if jumbo else RULE_TILE_H
    outline = tile.outline if not active else WHITE
    fill = tuple(min(channel + (16 if active else 0), 255) for channel in tile.fill)
    glow_rect(frame, (x, y, x + width, y + height), fill, outline, radius=16, width=3, glow=14)
    draw = ImageDraw.Draw(frame)
    font = chip_font(tile.text, width - 20, height - 18)
    draw_centered_text(draw, (x + width / 2.0, y + height / 2.0), tile.text, font, INK)


def draw_rule_sidebar(frame: Image.Image, rows: list[RuleRow], active_index: int | None = None) -> None:
    panel_height = 480
    draw_panel(frame, (26, 72, 408, 72 + panel_height), CYAN, radius=26)
    draw = ImageDraw.Draw(frame)
    draw.text((48, 92), "COMPLEX PUZZLE", font=HEAD_FONT, fill=WHITE)
    draw.text((50, 134), "reach USER / don't let LIE touch you", font=HUD_FONT, fill=(184, 231, 255))

    for idx, row in enumerate(rows):
        y = SIDEBAR_Y + idx * RULE_ROW_GAP
        is_active = idx == active_index or row.active
        for tile_index, tile in enumerate(row.pieces):
            x = SIDEBAR_X + tile_index * (RULE_TILE_W + 10)
            draw_rule_tile(frame, x, y, tile, active=is_active)


def make_rules(ctx_small: bool, door_open: bool) -> list[RuleRow]:
    return [
        RuleRow(
            (
                RuleTile("LLM", BLUE, CYAN),
                RuleTile("IS", WHITE, CYAN),
                RuleTile("YOU", CYAN, CYAN),
            )
        ),
        RuleRow(
            (
                RuleTile("USER", YELLOW, AMBER),
                RuleTile("IS", WHITE, CYAN),
                RuleTile("WIN", GREEN, GREEN),
            )
        ),
        RuleRow(
            (
                RuleTile("LIE", RED, PINK),
                RuleTile("IS", WHITE, CYAN),
                RuleTile("MOVE", PINK, PINK),
            )
        ),
        RuleRow(
            (
                RuleTile("CTX", VIOLET, CYAN),
                RuleTile("IS", WHITE, CYAN),
                RuleTile("SMALL" if ctx_small else "BIG", GREEN if ctx_small else VIOLET, GREEN if ctx_small else VIOLET),
            )
        ),
        RuleRow(
            (
                RuleTile("DOOR", AMBER, AMBER),
                RuleTile("IS", WHITE, CYAN),
                RuleTile("OPEN" if door_open else "SHUT", GREEN if door_open else AMBER, GREEN if door_open else AMBER),
            )
        ),
    ]


def draw_hint(frame: Image.Image, text: str, accent: tuple[int, int, int], x: float = 34, y: float = 26) -> None:
    draw = ImageDraw.Draw(frame)
    width = draw.textlength(text, font=LABEL_FONT) + 36
    glow_rect(frame, (x, y, x + width, y + 44), PANEL_ALT, accent, radius=16, width=3, glow=12)
    draw.text((x + 18, y + 8), text, font=LABEL_FONT, fill=WHITE)


def draw_board(frame: Image.Image, t: float) -> None:
    draw_panel(
        frame,
        (BOARD_X - 28, BOARD_Y - 28, BOARD_X + BOARD_COLS * CELL + 28, BOARD_Y + BOARD_ROWS * CELL + 28),
        outline=TEAL,
        radius=30,
    )
    draw = ImageDraw.Draw(frame)
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            x0, y0 = board_px(col, row)
            flicker = 18 + int(14 * math.sin(t * 1.9 + col * 0.7 + row * 0.5))
            color = (12 + flicker // 2, 24 + flicker, 40 + flicker)
            draw.rounded_rectangle((x0, y0, x0 + CELL - 8, y0 + CELL - 8), radius=16, fill=color)
            if (col + row) % 2 == 0:
                draw.rounded_rectangle((x0 + 6, y0 + 6, x0 + CELL - 14, y0 + CELL - 14), radius=12, outline=(58, 98, 128), width=1)


def draw_chip(frame: Image.Image, chip: Chip, scale: float = 1.0, ghost_alpha: int = 255) -> None:
    x, y = board_px(chip.col, chip.row)
    size = (CELL - 16) * scale
    left = x + (CELL - size) / 2.0 - 4
    top = y + (CELL - size) / 2.0 - 4
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    glow_rect(overlay, (left, top, left + size, top + size), chip.fill, chip.outline, radius=16, width=3, glow=10)
    overlay = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 0)), overlay, ghost_alpha / 255.0)
    frame.alpha_composite(overlay)
    draw = ImageDraw.Draw(frame)
    font = chip_font(chip.label, int(size - 20), int(size - 20))
    draw_centered_text(draw, (left + size / 2.0, top + size / 2.0), chip.label, font, INK)


def draw_big_context(frame: Image.Image, col: float, row: float, pulse: float) -> None:
    x, y = board_px(col, row)
    w = CELL * 2 - 14
    h = CELL * 2 - 14
    fill = (
        int(56 + 16 * pulse),
        int(54 + 16 * pulse),
        int(112 + 24 * pulse),
    )
    glow_rect(frame, (x, y, x + w, y + h), fill, VIOLET, radius=24, width=4, glow=20)
    draw = ImageDraw.Draw(frame)
    draw.text((x + 18, y + 18), "CTX", font=load_font(42, mono=True), fill=WHITE)
    draw.text((x + 18, y + 70), "CTX", font=load_font(42, mono=True), fill=(201, 188, 255))


def draw_avatar(frame: Image.Image, col: float, row: float, t: float, hue: tuple[int, int, int] = CYAN) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4
    cy = y + CELL / 2.0 - 4 + math.sin(t * 8.0 + col) * 3.0
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    glow_rect(overlay, (cx - 20, cy - 20, cx + 20, cy + 20), (232, 244, 255), hue, radius=16, width=3, glow=14)
    frame.alpha_composite(overlay)
    draw = ImageDraw.Draw(frame)
    draw.ellipse((cx - 8, cy - 4, cx - 3, cy + 1), fill=INK)
    draw.ellipse((cx + 3, cy - 4, cx + 8, cy + 1), fill=INK)
    draw.arc((cx - 9, cy + 1, cx + 9, cy + 11), start=15, end=165, fill=INK, width=2)


def draw_user(frame: Image.Image, col: float, row: float, t: float) -> None:
    x, y = board_px(col, row)
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    cx = x + CELL / 2.0 - 4
    cy = y + CELL / 2.0 - 4
    wobble = 2.0 * math.sin(t * 7.0)
    glow_rect(overlay, (cx - 26, cy - 18 + wobble, cx + 26, cy + 18 + wobble), (255, 244, 176), AMBER, radius=18, width=3, glow=16)
    frame.alpha_composite(overlay)
    draw = ImageDraw.Draw(frame)
    draw.polygon([(cx - 10, cy + 17), (cx - 1, cy + 28), (cx + 3, cy + 16)], fill=(255, 244, 176), outline=AMBER)
    draw.text((cx - 18, cy - 10), "hi", font=HUD_FONT, fill=INK)


def draw_lie(frame: Image.Image, col: float, row: float, t: float, intensity: float = 1.0) -> None:
    x, y = board_px(col, row)
    cx = x + CELL / 2.0 - 4 + math.sin(t * 10.0 + col * 0.5) * 6.0 * intensity
    cy = y + CELL / 2.0 - 4 + math.cos(t * 13.0 + row * 0.6) * 5.0 * intensity
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    glow = ImageDraw.Draw(overlay)
    points: list[tuple[float, float]] = []
    for idx in range(10):
        angle = idx * (math.tau / 10.0)
        radius = 18 if idx % 2 == 0 else 8
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    glow.polygon(points, fill=RED + (210,), outline=PINK + (255,))
    for offset in (-8, 0, 8):
        glow.line((cx - 18, cy + offset, cx + 18, cy + offset), fill=(255, 198, 222, 150), width=2)
    frame.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(5)))
    frame.alpha_composite(overlay)


def draw_door(frame: Image.Image, openness: float) -> None:
    openness = clamp(openness, 0.0, 1.0)
    x = BOARD_X + CELL * 8.0 + 12
    top = BOARD_Y + CELL * 1.4
    bottom = BOARD_Y + CELL * 5.2
    left_bar = x - lerp(0.0, 24.0, openness)
    right_bar = x + 36 + lerp(0.0, 24.0, openness)
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = int(255 * (1.0 - openness * 0.92))
    for bar_x in (left_bar, right_bar):
        draw.rounded_rectangle((bar_x, top, bar_x + 12, bottom), radius=8, fill=AMBER + (alpha,), outline=YELLOW + (alpha,))
    frame.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(6)))
    frame.alpha_composite(overlay)


def big_context_positions() -> list[tuple[float, float]]:
    return [(2.0, 0.4), (4.1, 2.4), (2.8, 4.2)]


def stacked_context_positions() -> list[tuple[float, float]]:
    return [(2.0, 5.2), (3.0, 5.2), (4.0, 5.2), (2.5, 4.2), (3.5, 4.2)]


def cage_positions() -> list[tuple[float, float]]:
    return [(3.2, 1.0), (4.2, 1.0), (5.2, 1.0), (3.2, 2.0), (5.2, 2.0), (3.2, 3.0), (4.2, 3.0), (5.2, 3.0)]


def interpolate_points(start: list[tuple[float, float]], end: list[tuple[float, float]], t: float) -> list[tuple[float, float]]:
    return [(lerp(a[0], b[0], t), lerp(a[1], b[1], t)) for a, b in zip(start, end)]


def render_board_state(frame: Image.Image, t: float, ctx_small: bool, lies_caged: float, door_open: float, avatar: tuple[float, float]) -> None:
    draw_board(frame, t)
    pulse = 0.55 + 0.45 * math.sin(t * 4.0)
    if not ctx_small:
        for col, row in big_context_positions():
            draw_big_context(frame, col, row, pulse)
    else:
        chips_from = stacked_context_positions()
        chips_to = cage_positions()
        chip_positions = interpolate_points(chips_from, chips_to, lies_caged)
        for idx, (col, row) in enumerate(chip_positions):
            draw_chip(frame, Chip("CTX", col, row, (36, 48, 102), VIOLET))
            if idx >= 5 and lies_caged < 0.18:
                draw_chip(frame, Chip("CTX", chips_from[idx - 5][0], chips_from[idx - 5][1], (36, 48, 102), VIOLET), scale=0.6, ghost_alpha=90)

    lie_start = [(4.2, 4.2), (5.0, 3.5), (5.6, 4.4)]
    lie_end = [(4.1, 1.6), (4.6, 2.2), (4.7, 1.4)]
    for col, row in interpolate_points(lie_start, lie_end, lies_caged):
        draw_lie(frame, col, row, t, intensity=1.0 - lies_caged * 0.15)

    draw_door(frame, door_open)
    draw_user(frame, 8.7, 2.8, t)
    draw_avatar(frame, avatar[0], avatar[1], t)


def render_setup(frame: Image.Image, t: float) -> None:
    draw_rule_sidebar(frame, make_rules(ctx_small=False, door_open=False), active_index=3)
    render_board_state(frame, t, ctx_small=False, lies_caged=0.0, door_open=0.0, avatar=(0.8, 5.3))
    draw_hint(frame, "WAY TOO MUCH CONTEXT", VIOLET)


def render_ctx_patch(frame: Image.Image, t: float) -> None:
    local = t - 2.8
    progress = ease_out_cubic(local / 2.2)
    draw_rule_sidebar(frame, make_rules(ctx_small=False, door_open=False), active_index=3)
    render_board_state(frame, t, ctx_small=False, lies_caged=0.0, door_open=0.0, avatar=(0.8, 5.3))
    veil = Image.new("RGBA", frame.size, (5, 8, 14, 170))
    frame.alpha_composite(veil)

    draw = ImageDraw.Draw(frame)
    focus = (320, 200, 1180, 520)
    glow_rect(frame, focus, PANEL_ALT, GREEN, radius=26, width=4, glow=18)

    tiles = [
        RuleTile("CTX", VIOLET, CYAN),
        RuleTile("IS", WHITE, CYAN),
    ]
    for idx, tile in enumerate(tiles):
        draw_rule_tile(frame, 394 + idx * 170, 300, tile, jumbo=True)

    old_shift = 280.0 * ease_out_cubic(clamp((local - 0.28) / 0.52, 0.0, 1.0))
    if local < 1.0:
        draw_rule_tile(frame, 734 + old_shift, 300 - old_shift * 0.06, RuleTile("BIG", VIOLET, VIOLET), jumbo=True)

    incoming_y = lerp(126.0, 300.0, progress)
    incoming_x = lerp(980.0, 734.0, progress)
    for ghost_idx in range(3):
        ghost_progress = clamp(progress - ghost_idx * 0.08, 0.0, 1.0)
        ghost_x = lerp(1060.0, 734.0, ghost_progress)
        ghost_y = lerp(100.0, 300.0, ghost_progress)
        draw_rule_tile(
            frame,
            ghost_x - ghost_idx * 6,
            ghost_y,
            RuleTile("SMALL", GREEN, LIME),
            jumbo=True,
        )
        if ghost_idx < 2:
            frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 0)))
    draw_rule_tile(frame, incoming_x, incoming_y, RuleTile("SMALL", GREEN, LIME), jumbo=True, active=True)

    if local > 0.7:
        flash = int(120 * math.sin((local - 0.7) * 22.0) ** 2)
        draw.text((374, 234), "SUMMARIZE FIRST", font=BIG_FONT, fill=(255, 255, 255, 120 + flash))
    draw_hint(frame, "SUMMARIZE FIRST", GREEN)


def render_midgame(frame: Image.Image, t: float) -> None:
    local = t - 5.0
    progress = ease_in_out(local / 4.8)
    avatar = (lerp(0.8, 4.2, progress), lerp(5.3, 4.0, progress))
    draw_rule_sidebar(frame, make_rules(ctx_small=True, door_open=False), active_index=None)
    render_board_state(frame, t, ctx_small=True, lies_caged=progress, door_open=0.0, avatar=avatar)

    if progress > 0.18:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        path_points = [board_px(2.4, 4.4), board_px(3.0, 3.2), board_px(4.6, 2.7), board_px(5.2, 1.7)]
        flattened = [(x + CELL / 2.0 - 4, y + CELL / 2.0 - 4) for x, y in path_points]
        overlay_draw.line(flattened, fill=CYAN + (160,), width=8)
        frame.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(6)))

    draw_hint(frame, "TURN NOTES INTO WALLS", CYAN)


def render_door_patch(frame: Image.Image, t: float) -> None:
    local = t - 9.8
    progress = ease_out_cubic(local / 2.4)
    draw_rule_sidebar(frame, make_rules(ctx_small=True, door_open=False), active_index=4)
    render_board_state(frame, t, ctx_small=True, lies_caged=1.0, door_open=0.0, avatar=(4.2, 4.0))
    veil = Image.new("RGBA", frame.size, (5, 8, 14, 156))
    frame.alpha_composite(veil)

    focus = (280, 208, 1180, 510)
    glow_rect(frame, focus, PANEL_ALT, AMBER, radius=26, width=4, glow=18)

    tiles = [
        RuleTile("DOOR", AMBER, AMBER),
        RuleTile("IS", WHITE, CYAN),
    ]
    for idx, tile in enumerate(tiles):
        draw_rule_tile(frame, 352 + idx * 180, 300, tile, jumbo=True)

    shut_shift = 240.0 * ease_out_cubic(clamp((local - 0.3) / 0.52, 0.0, 1.0))
    if local < 0.95:
        draw_rule_tile(frame, 712 + shut_shift, 300, RuleTile("SHUT", AMBER, AMBER), jumbo=True)

    for echo in range(3):
        echo_progress = clamp(progress - echo * 0.1, 0.0, 1.0)
        x = lerp(1010.0, 712.0, echo_progress)
        y = lerp(140.0, 300.0, echo_progress)
        draw_rule_tile(frame, x - echo * 6, y, RuleTile("OPEN", GREEN, LIME), jumbo=True, active=echo == 0)

    draw = ImageDraw.Draw(frame)
    if local > 0.8:
        draw.text((342, 234), "PATCH THE GATE", font=BIG_FONT, fill=(255, 245, 222))
    draw_hint(frame, "PATCH THE GATE", AMBER)


def render_final(frame: Image.Image, t: float) -> None:
    local = t - 12.2
    progress = ease_in_out(local / 3.0)
    avatar = (lerp(4.2, 8.3, progress), lerp(4.0, 2.9, progress))
    draw_rule_sidebar(frame, make_rules(ctx_small=True, door_open=True))
    render_board_state(frame, t, ctx_small=True, lies_caged=1.0, door_open=progress, avatar=avatar)
    draw_hint(frame, "SHIP THE ANSWER", LIME)

    if progress > 0.7:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        glow = ImageDraw.Draw(overlay)
        ux, uy = board_px(8.7, 2.8)
        cx = ux + CELL / 2.0 - 4
        cy = uy + CELL / 2.0 - 4
        for idx in range(18):
            angle = idx * (math.tau / 18.0)
            length = 60 + 120 * progress + 20 * math.sin(local * 11.0 + idx)
            glow.line((cx, cy, cx + math.cos(angle) * length, cy + math.sin(angle) * length), fill=(255, 243, 202, 200), width=3)
        frame.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(3)))
        frame.alpha_composite(overlay)

        banner = (362, 146, 1040, 238)
        glow_rect(frame, banner, PANEL_ALT, GREEN, radius=24, width=4, glow=20)
        draw = ImageDraw.Draw(frame)
        draw.text((394, 160), "CONTEXT FITS", font=BIG_FONT, fill=WHITE)
        draw_hint(frame, "still statistically guessing", YELLOW, x=840, y=632)


def render_frame(frame_index: int) -> Image.Image:
    t = frame_index / FPS
    frame = make_background(t)
    if t < 2.8:
        render_setup(frame, t)
    elif t < 5.0:
        render_ctx_patch(frame, t)
    elif t < 9.8:
        render_midgame(frame, t)
    elif t < 12.2:
        render_door_patch(frame, t)
    else:
        render_final(frame, t)
    return frame.convert("RGB")


def add_wave(buffer: np.ndarray, start: float, end: float, frequency: float, amplitude: float, kind: str = "sine") -> None:
    start_idx = int(start * SAMPLE_RATE)
    end_idx = min(int(end * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    segment_t = np.arange(end_idx - start_idx, dtype=np.float32) / SAMPLE_RATE
    envelope = np.clip(np.sin(np.linspace(0.0, math.pi, end_idx - start_idx, dtype=np.float32)), 0.0, None) ** 0.85
    phase = 2.0 * math.pi * frequency * segment_t
    if kind == "square":
        wave_part = np.sign(np.sin(phase))
    elif kind == "saw":
        wave_part = 2.0 * ((segment_t * frequency) % 1.0) - 1.0
    else:
        wave_part = np.sin(phase)
    buffer[start_idx:end_idx] += wave_part * envelope * amplitude


def add_noise_hit(buffer: np.ndarray, when: float, duration: float, amplitude: float) -> None:
    start_idx = int(when * SAMPLE_RATE)
    end_idx = min(int((when + duration) * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    noise = np.random.default_rng(4242 + start_idx).standard_normal(end_idx - start_idx).astype(np.float32)
    envelope = np.linspace(1.0, 0.0, end_idx - start_idx, dtype=np.float32) ** 2.2
    buffer[start_idx:end_idx] += noise * envelope * amplitude


def add_chirp(buffer: np.ndarray, start: float, duration: float, freq_a: float, freq_b: float, amplitude: float) -> None:
    start_idx = int(start * SAMPLE_RATE)
    end_idx = min(int((start + duration) * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    count = end_idx - start_idx
    segment_t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    freqs = np.linspace(freq_a, freq_b, count, dtype=np.float32)
    phase = np.cumsum(2.0 * math.pi * freqs / SAMPLE_RATE)
    envelope = np.clip(np.sin(np.linspace(0.0, math.pi, count, dtype=np.float32)), 0.0, None)
    buffer[start_idx:end_idx] += np.sin(phase) * envelope * amplitude


def build_audio() -> np.ndarray:
    samples = int(DURATION * SAMPLE_RATE)
    audio = np.zeros(samples, dtype=np.float32)

    scenes = [
        (0.0, 2.8, 82.0, "saw", 0.06),
        (2.8, 5.0, 98.0, "square", 0.08),
        (5.0, 9.8, 110.0, "saw", 0.06),
        (9.8, 12.2, 130.0, "square", 0.08),
        (12.2, 18.0, 146.0, "saw", 0.07),
    ]
    for start, end, freq, kind, amp in scenes:
        add_wave(audio, start, end, freq, amp, kind)
        add_wave(audio, start, end, freq * 2.0, amp * 0.32, "sine")
        add_wave(audio, start, end, freq * 0.5, amp * 0.18, "sine")

    arp = [
        (0.16, 392.0), (0.42, 466.0), (0.68, 523.0), (0.94, 659.0),
        (2.92, 784.0), (3.12, 988.0), (3.28, 1174.0), (3.46, 1396.0),
        (5.30, 392.0), (5.86, 440.0), (6.42, 523.0), (6.98, 659.0),
        (7.54, 392.0), (8.10, 466.0), (8.66, 523.0),
        (10.08, 698.0), (10.30, 880.0), (10.52, 1046.0), (10.76, 1318.0),
        (12.56, 523.0), (12.86, 659.0), (13.16, 784.0), (13.46, 988.0),
        (14.00, 1174.0), (14.42, 1318.0), (14.84, 1568.0), (15.32, 1318.0),
    ]
    for when, freq in arp:
        add_wave(audio, when, when + 0.12, freq, 0.12, "square")

    for when in (2.9, 3.08, 3.22, 3.36, 10.08, 10.24, 10.38, 10.54):
        add_chirp(audio, when, 0.12, 420.0, 2200.0, 0.08)

    kicks = [0.0, 0.72, 1.44, 2.16, 5.28, 6.00, 6.72, 7.44, 8.16, 8.88, 12.24, 12.96, 13.68, 14.40, 15.12, 15.84, 16.56]
    for when in kicks:
        add_noise_hit(audio, when, 0.08, 0.10)
        add_wave(audio, when, when + 0.10, 58.0, 0.11, "sine")

    fade = np.linspace(1.0, 0.0, int(SAMPLE_RATE * 0.8), dtype=np.float32)
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
    parser = argparse.ArgumentParser(description="Render a more complex Baba-style LLM YTP.")
    parser.add_argument("--workdir", required=True, help="Directory for generated outputs.")
    parser.add_argument("--sample-times", help="Comma-separated list of preview times in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    if args.sample_times:
        sample_dir = workdir / "samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        for time_point in parse_sample_times(args.sample_times):
            frame_index = int(clamp(round(time_point * FPS), 0, FRAME_COUNT - 1))
            frame = render_frame(frame_index)
            label = f"{time_point:05.2f}".replace(".", "_")
            frame.save(sample_dir / f"sample_{label}.png", compress_level=1)
        return

    frames_dir = workdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_index in range(FRAME_COUNT):
        render_frame(frame_index).save(frames_dir / f"frame_{frame_index:05d}.png", compress_level=1)

    audio = build_audio()
    write_wav(workdir / "audio.wav", audio)
    (workdir / "storyboard.txt").write_text(
        "\n".join(
            [
                "0.0-2.8 setup: too much context blocks the route",
                "2.8-5.0 patch: CTX IS BIG -> CTX IS SMALL",
                "5.0-9.8 midgame: use summarized context to cage the lies",
                "9.8-12.2 patch: DOOR IS SHUT -> DOOR IS OPEN",
                "12.2-18.0 ending: cross the cleaned corridor and reach USER",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
