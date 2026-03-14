#!/usr/bin/env python3
from __future__ import annotations

import argparse
from functools import lru_cache
import math
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 24
DURATION = 16.5
SAMPLE_RATE = 48_000
FRAME_COUNT = int(FPS * DURATION)

BOARD_COLS = 13
BOARD_ROWS = 8
CELL = 62
BOARD_X = 235
BOARD_Y = 150

BG_TOP = np.array((18, 11, 9), dtype=np.float32)
BG_BOTTOM = np.array((72, 37, 27), dtype=np.float32)
INK = (31, 23, 19)
CREAM = (248, 229, 184)
CYAN = (104, 238, 255)
RED = (239, 81, 67)
YELLOW = (255, 214, 74)
GREEN = (126, 245, 163)
BLUE = (99, 155, 255)


@dataclass(frozen=True)
class Tile:
    text: str
    col: float
    row: float
    fill: tuple[int, int, int]


def ease_out_cubic(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1.0 - (1.0 - x) ** 3


def ease_in_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def to_px(col: float, row: float) -> tuple[float, float]:
    return BOARD_X + col * CELL, BOARD_Y + row * CELL


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


TITLE_FONT = load_font(56, bold=True)
HUGE_FONT = load_font(74, bold=True)
BODY_FONT = load_font(28, bold=True)
SMALL_FONT = load_font(22, bold=True)
TILE_FONT = load_font(24, bold=True)


def make_background(t: float) -> Image.Image:
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        mix = y / max(HEIGHT - 1, 1)
        base = BG_TOP * (1.0 - mix) + BG_BOTTOM * mix
        stripe = 18.0 * math.sin((y / HEIGHT) * 17.0 + t * 1.8)
        row = np.clip(base + stripe, 0.0, 255.0)
        canvas[y, :, :] = row.astype(np.uint8)
    image = Image.fromarray(canvas)
    draw = ImageDraw.Draw(image)

    for idx in range(16):
        offset = (t * 140.0 + idx * 97.0) % (WIDTH + 220)
        x0 = int(offset) - 180
        draw.polygon(
            [(x0, 0), (x0 + 160, 0), (x0 + 40, HEIGHT), (x0 - 120, HEIGHT)],
            fill=(255, 255, 255, 0),
        )

    for idx in range(11):
        jitter = math.sin(t * 2.2 + idx) * 9.0
        x = 52 + idx * 108 + jitter
        draw.line((x, 0, x - 72, HEIGHT), fill=(128, 67, 51), width=2)

    return image


def draw_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float, float, float],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    radius: int = 12,
    width: int = 3,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_center(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((center[0] - w / 2.0, center[1] - h / 2.0 - 2.0), text, font=font, fill=fill)


def highlight_tile(draw: ImageDraw.ImageDraw, col: float, row: float, color: tuple[int, int, int], pulse: float = 0.0) -> None:
    x, y = to_px(col, row)
    inset = 1.0 + pulse
    draw.rounded_rectangle(
        (x + inset, y + inset, x + CELL - inset - 6, y + CELL - inset - 6),
        radius=12,
        outline=color,
        width=4,
    )


@lru_cache(maxsize=32)
def tile_font_for(text: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    max_width = CELL - 20
    max_height = CELL - 24
    for size in range(28, 9, -1):
        font = load_font(size, bold=True)
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font
    return load_font(10, bold=True)


def draw_word_tile(draw: ImageDraw.ImageDraw, tile: Tile, shake: float = 0.0, scale: float = 1.0) -> None:
    x, y = to_px(tile.col, tile.row)
    cx = x + CELL / 2.0 + math.sin(tile.col * 1.2 + tile.row * 0.4) * shake
    cy = y + CELL / 2.0 + math.cos(tile.row * 0.8 + tile.col * 0.2) * shake
    half = (CELL - 9) * scale / 2.0
    rect = (cx - half, cy - half, cx + half, cy + half)
    draw_box(draw, rect, fill=CREAM, outline=INK, radius=10, width=3)
    inner = (rect[0] + 6, rect[1] + 6, rect[2] - 6, rect[3] - 6)
    draw_box(draw, inner, fill=tile.fill, outline=INK, radius=8, width=2)
    draw_text_center(draw, (cx, cy), tile.text, tile_font_for(tile.text), INK)


def draw_grid(draw: ImageDraw.ImageDraw, t: float, pulse: float = 0.0) -> None:
    board_rect = (
        BOARD_X - 16,
        BOARD_Y - 16,
        BOARD_X + BOARD_COLS * CELL + 16,
        BOARD_Y + BOARD_ROWS * CELL + 16,
    )
    draw_box(draw, board_rect, fill=(34, 21, 18), outline=(244, 212, 158), radius=22, width=4)
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            x0, y0 = to_px(col, row)
            value = 24 + int(12 * math.sin(t * 2.0 + col * 0.8 + row * 0.5) + pulse * 12)
            fill = (value + 10, value, value - 4)
            draw.rounded_rectangle((x0, y0, x0 + CELL - 6, y0 + CELL - 6), radius=10, fill=fill)


def draw_assistant(draw: ImageDraw.ImageDraw, col: float, row: float, t: float, scale: float = 1.0) -> None:
    x, y = to_px(col, row)
    cx = x + CELL / 2.0
    cy = y + CELL / 2.0 + math.sin(t * 8.0 + col) * 3.0
    half = 18.0 * scale
    draw.rounded_rectangle(
        (cx - half, cy - half, cx + half, cy + half),
        radius=12,
        fill=(244, 250, 255),
        outline=CYAN,
        width=3,
    )
    draw.ellipse((cx - 9, cy - 5, cx - 3, cy + 1), fill=INK)
    draw.ellipse((cx + 3, cy - 5, cx + 9, cy + 1), fill=INK)
    mouth = 5.0 + 3.0 * math.sin(t * 6.0)
    draw.arc((cx - 8, cy + 1, cx + 8, cy + 10 + mouth), start=15, end=165, fill=INK, width=2)


def draw_user(draw: ImageDraw.ImageDraw, col: float, row: float, t: float, scale: float = 1.0) -> None:
    x, y = to_px(col, row)
    cx = x + CELL / 2.0
    cy = y + CELL / 2.0
    outer = 20.0 * scale + 2.0 * math.sin(t * 5.0)
    inner = outer * 0.42
    points: list[tuple[float, float]] = []
    for idx in range(10):
        angle = -math.pi / 2.0 + idx * math.pi / 5.0
        radius = outer if idx % 2 == 0 else inner
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=YELLOW, outline=INK)
    draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(255, 255, 226))


def draw_hallucination(draw: ImageDraw.ImageDraw, col: float, row: float, t: float, scale: float = 1.0) -> None:
    x, y = to_px(col, row)
    cx = x + CELL / 2.0
    cy = y + CELL / 2.0
    points: list[tuple[float, float]] = []
    for idx in range(16):
        angle = (math.tau / 16.0) * idx
        radius = (16.0 + 4.0 * math.sin(t * 10.0 + idx * 0.9)) * scale
        if idx % 2:
            radius *= 0.68
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=RED, outline=INK)
    draw.rectangle((cx - 6, cy - 2, cx + 6, cy + 2), fill=(255, 220, 214))
    draw.rectangle((cx - 2, cy - 6, cx + 2, cy + 6), fill=(255, 220, 214))


def draw_hint(
    draw: ImageDraw.ImageDraw,
    text: str,
    accent: tuple[int, int, int],
    x: float = 60,
    y: float = 46,
) -> None:
    width = draw.textlength(text, font=BODY_FONT) + 34
    rect = (x, y, x + width, y + 42)
    draw_box(draw, rect, fill=(24, 17, 15), outline=accent, radius=14, width=3)
    draw.text((x + 16, y + 8), text, font=BODY_FONT, fill=(255, 240, 214))


def base_rule_tiles(push_mode: bool) -> list[Tile]:
    predicate_fill = GREEN if push_mode else RED
    return [
        Tile("LLM", 0, 0, BLUE),
        Tile("IS", 1, 0, CREAM),
        Tile("YOU", 2, 0, CYAN),
        Tile("USER", 0, 1, YELLOW),
        Tile("IS", 1, 1, CREAM),
        Tile("WIN", 2, 1, GREEN),
        Tile("LIE", 0, 2, RED),
        Tile("IS", 1, 2, CREAM),
        Tile("PUSH" if push_mode else "LOSE", 2, 2, predicate_fill),
    ]


def draw_board_scene(image: Image.Image, t: float, push_mode: bool, assistant_pos: tuple[float, float], hazards: list[tuple[float, float]]) -> None:
    draw = ImageDraw.Draw(image)
    draw_grid(draw, t, pulse=0.2 if push_mode else 0.0)
    for tile in base_rule_tiles(push_mode):
        draw_word_tile(draw, tile, shake=1.2 if not push_mode else 0.7)
    extra_tiles = [Tile("PUSH", 5.1, 6.0, GREEN)]
    if push_mode:
        extra_tiles[0] = Tile("LOSE", 5.1, 6.0, RED)
    for tile in extra_tiles:
        draw_word_tile(draw, tile, shake=1.0)

    for col, row in hazards:
        draw_hallucination(draw, col, row, t)
    draw_user(draw, 10.9, 4.0, t)
    draw_assistant(draw, assistant_pos[0], assistant_pos[1], t)


def render_title_frame(image: Image.Image, t: float) -> None:
    hazards = [(4.7, 4.0), (5.8, 4.0), (6.9, 4.0), (8.0, 4.0)]
    draw_board_scene(image, t, push_mode=False, assistant_pos=(1.1, 4.0), hazards=hazards)
    draw = ImageDraw.Draw(image)
    pulse = 1.5 * (0.5 + 0.5 * math.sin(t * 11.0))
    highlight_tile(draw, 2, 2, RED, pulse=pulse)
    highlight_tile(draw, 5.1, 6.0, GREEN, pulse=1.2 - pulse * 0.35)
    draw_hint(draw, "NO PATH", RED)
    draw_hint(draw, "RULEHACK", GREEN, y=98)


def render_intro_board(image: Image.Image, t: float) -> None:
    local = t - 0.9
    progress = ease_in_out(clamp(local / 3.7, 0.0, 1.0))
    assistant_x = lerp(1.1, 4.6, progress)
    assistant_y = lerp(4.0, 5.9, progress) + math.sin(local * 7.0) * 0.04
    hazards = [(4.7, 4.0), (5.8, 4.0), (6.9, 4.0), (8.0, 4.0)]
    draw_board_scene(image, t, push_mode=False, assistant_pos=(assistant_x, assistant_y), hazards=hazards)
    draw = ImageDraw.Draw(image)
    highlight_tile(draw, 2, 2, RED, pulse=1.4)
    highlight_tile(draw, 5.1, 6.0, GREEN, pulse=1.1)
    draw_hint(draw, "LOSE -> PUSH", CYAN)


def render_rule_hack(image: Image.Image, t: float) -> None:
    local = t - 4.6
    progress = ease_out_cubic(local / 2.4)
    draw = ImageDraw.Draw(image)
    draw_box(draw, (112, 160, WIDTH - 112, 420), fill=(24, 17, 15), outline=GREEN, radius=28, width=4)

    slots = [
        Tile("LIE", 2.5, 3.0, RED),
        Tile("IS", 4.4, 3.0, CREAM),
    ]
    for tile in slots:
        draw_word_tile(draw, tile, shake=1.6)

    defeat_shift = 240.0 * ease_out_cubic(clamp((local - 0.5) / 0.55, 0.0, 1.0))
    if local < 1.0:
        x, y = to_px(6.3, 3.0)
        rect = (x + 4 + defeat_shift, y + 4 - defeat_shift * 0.18, x + CELL - 4 + defeat_shift, y + CELL - 4 - defeat_shift * 0.18)
        draw_box(draw, rect, fill=CREAM, outline=INK, radius=10, width=3)
        inner = (rect[0] + 6, rect[1] + 6, rect[2] - 6, rect[3] - 6)
        draw_box(draw, inner, fill=RED, outline=INK, radius=8, width=2)
        draw_text_center(draw, ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0), "LOSE", tile_font_for("LOSE"), INK)

    incoming_x = lerp(2.4, 6.3, progress)
    slam_scale = 1.0 + 0.16 * math.sin(progress * math.pi * 7.0) * (1.0 - progress)
    if local < 1.1:
        for ghost_idx, ghost_x in enumerate((incoming_x - 0.55, incoming_x - 1.05)):
            fill = (176 - ghost_idx * 18, 240, 176 - ghost_idx * 18)
            draw_word_tile(
                draw,
                Tile("PUSH", ghost_x, 4.8 - progress * 1.45 + ghost_idx * 0.08, fill),
                shake=0.9,
                scale=0.92 - ghost_idx * 0.08,
            )
    draw_word_tile(draw, Tile("PUSH", incoming_x, 4.6 - progress * 1.6, GREEN), shake=3.0 * (1.0 - progress), scale=slam_scale)

    if local > 1.2:
        draw.text((310, 322), "LIE IS PUSH", font=HUGE_FONT, fill=(255, 244, 215))

    draw_hint(draw, "SHOVE PUSH IN", GREEN)


def render_push_board(image: Image.Image, t: float) -> None:
    local = t - 7.0
    move = ease_in_out(clamp(local / 4.8, 0.0, 1.0))
    assistant_x = lerp(4.6, 9.6, move)
    assistant_y = 4.0 + math.sin(local * 3.0) * 0.05
    hazards = [
        (lerp(4.7, 4.2, move), lerp(4.0, 2.7, move)),
        (lerp(5.8, 5.3, move), lerp(4.0, 5.5, move)),
        (lerp(6.9, 7.5, move), lerp(4.0, 2.4, move)),
        (lerp(8.0, 8.6, move), lerp(4.0, 5.8, move)),
    ]
    draw_board_scene(image, t, push_mode=True, assistant_pos=(assistant_x, assistant_y), hazards=hazards)
    draw = ImageDraw.Draw(image)
    draw_hint(draw, "BONK THE RED STUFF", CYAN)


def render_final_approach(image: Image.Image, t: float) -> None:
    local = t - 11.8
    move = ease_in_out(clamp(local / 1.2, 0.0, 1.0))
    assistant_x = lerp(9.6, 10.6, move)
    hazards = [(4.2, 2.7), (5.3, 5.5), (7.5, 2.4), (8.6, 5.8)]
    draw_board_scene(image, t, push_mode=True, assistant_pos=(assistant_x, 4.0 + math.sin(local * 5.0) * 0.03), hazards=hazards)
    draw = ImageDraw.Draw(image)
    draw_hint(draw, "GET USER", YELLOW)


def render_win(image: Image.Image, t: float) -> None:
    local = t - 13.0
    win_progress = ease_out_cubic(clamp(local / 1.4, 0.0, 1.0))
    assistant_x = lerp(10.6, 10.9, win_progress)
    hazards = [(4.2, 2.7), (5.3, 5.5), (7.5, 2.4), (8.6, 5.8)]
    draw_board_scene(image, t, push_mode=True, assistant_pos=(assistant_x, 4.0), hazards=hazards)
    draw = ImageDraw.Draw(image)

    burst_radius = 40 + 220 * win_progress
    center = to_px(10.9, 4.0)
    center = (center[0] + CELL / 2.0, center[1] + CELL / 2.0)
    for idx in range(18):
        angle = idx * (math.tau / 18.0)
        length = burst_radius + 18 * math.sin(local * 12.0 + idx)
        draw.line(
            (
                center[0],
                center[1],
                center[0] + math.cos(angle) * length,
                center[1] + math.sin(angle) * length,
            ),
            fill=(255, 240, 188),
            width=4,
        )

    if local > 0.2:
        big = "USER IS WIN"
        bbox = draw.textbbox((0, 0), big, font=HUGE_FONT)
        w = bbox[2] - bbox[0]
        draw_box(draw, ((WIDTH - w) / 2.0 - 24, 138, (WIDTH + w) / 2.0 + 24, 228), fill=(23, 19, 15), outline=GREEN, radius=22, width=4)
        draw.text(((WIDTH - w) / 2.0, 156), big, font=HUGE_FONT, fill=(255, 246, 214))

    if local > 0.35:
        draw_hint(draw, "still rotating internally", YELLOW, x=WIDTH - 430, y=620)

    if local > 2.2:
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(0, 0, 0))


def render_frame(frame_index: int) -> Image.Image:
    t = frame_index / FPS
    image = make_background(t)
    if t < 0.9:
        render_title_frame(image, t)
    elif t < 4.6:
        render_intro_board(image, t)
    elif t < 7.0:
        render_rule_hack(image, t)
    elif t < 11.8:
        render_push_board(image, t)
    elif t < 13.0:
        render_final_approach(image, t)
    else:
        render_win(image, t)
    return image


def add_waveform(buffer: np.ndarray, start: float, end: float, frequency: float, amplitude: float, mode: str = "sine") -> None:
    start_idx = int(start * SAMPLE_RATE)
    end_idx = min(int(end * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    segment_t = np.arange(end_idx - start_idx, dtype=np.float32) / SAMPLE_RATE
    envelope = np.clip(
        np.sin(np.linspace(0.0, math.pi, end_idx - start_idx, dtype=np.float32)),
        0.0,
        None,
    ) ** 0.75
    phase = 2.0 * math.pi * frequency * segment_t
    if mode == "square":
        wave_part = np.sign(np.sin(phase))
    elif mode == "saw":
        wave_part = 2.0 * ((segment_t * frequency) % 1.0) - 1.0
    else:
        wave_part = np.sin(phase)
    buffer[start_idx:end_idx] += wave_part * envelope * amplitude


def add_noise_hit(buffer: np.ndarray, time_point: float, duration: float, amplitude: float) -> None:
    start_idx = int(time_point * SAMPLE_RATE)
    end_idx = min(int((time_point + duration) * SAMPLE_RATE), buffer.shape[0])
    if end_idx <= start_idx:
        return
    noise = np.random.default_rng(8 + start_idx).standard_normal(end_idx - start_idx).astype(np.float32)
    envelope = np.linspace(1.0, 0.0, end_idx - start_idx, dtype=np.float32) ** 2.0
    buffer[start_idx:end_idx] += noise * envelope * amplitude


def build_audio(total_duration: float) -> np.ndarray:
    total_samples = int(total_duration * SAMPLE_RATE)
    audio = np.zeros(total_samples, dtype=np.float32)

    scene_tones = [
        (0.0, 1.8, 110.0, "saw", 0.07),
        (1.8, 4.8, 138.0, "square", 0.06),
        (4.8, 7.2, 174.0, "saw", 0.085),
        (7.2, 10.8, 156.0, "square", 0.07),
        (10.8, 13.8, 124.0, "sine", 0.05),
        (13.8, 16.5, 196.0, "square", 0.08),
    ]
    for start, end, freq, mode, amp in scene_tones:
        add_waveform(audio, start, end, freq, amp, mode=mode)
        add_waveform(audio, start, end, freq * 2.0, amp * 0.36, mode="sine")

    melody = [
        (0.15, 440.0),
        (0.48, 554.0),
        (0.82, 659.0),
        (1.15, 740.0),
        (2.15, 392.0),
        (2.80, 466.0),
        (3.55, 392.0),
        (4.15, 349.0),
        (5.10, 622.0),
        (5.22, 698.0),
        (5.34, 830.0),
        (5.52, 932.0),
        (6.20, 698.0),
        (7.38, 392.0),
        (8.10, 440.0),
        (8.84, 392.0),
        (9.52, 330.0),
        (10.18, 262.0),
        (11.02, 294.0),
        (11.48, 262.0),
        (12.40, 220.0),
        (13.92, 523.0),
        (14.16, 659.0),
        (14.42, 784.0),
        (14.66, 988.0),
        (15.10, 1174.0),
    ]
    for time_point, freq in melody:
        add_waveform(audio, time_point, time_point + 0.14, freq, 0.12, mode="square")

    hits = [0.0, 1.8, 4.8, 5.32, 7.2, 10.8, 13.8, 14.3, 14.9]
    for hit in hits:
        add_noise_hit(audio, hit, 0.12, 0.13)

    buzz_times = np.arange(5.0, 5.7, 0.08)
    for hit in buzz_times:
        add_waveform(audio, float(hit), float(hit) + 0.05, 990.0, 0.06, mode="sine")

    fade_out = np.linspace(1.0, 0.0, int(SAMPLE_RATE * 0.6), dtype=np.float32)
    audio[-fade_out.shape[0] :] *= fade_out
    audio = np.clip(audio, -0.95, 0.95)
    return audio


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())


def parse_sample_times(raw: str) -> list[float]:
    times: list[float] = []
    for value in raw.split(","):
        value = value.strip()
        if not value:
            continue
        times.append(float(value))
    return times


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a short Baba-is-You style LLM YTP asset pack.")
    parser.add_argument("--workdir", required=True, help="Directory for generated frames and audio.")
    parser.add_argument(
        "--sample-times",
        help="Comma-separated times in seconds to render preview frames only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).resolve()
    frames_dir = workdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    if args.sample_times:
        samples_dir = workdir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        for time_point in parse_sample_times(args.sample_times):
            frame_idx = int(clamp(round(time_point * FPS), 0, FRAME_COUNT - 1))
            image = render_frame(frame_idx)
            label = f"{time_point:05.2f}".replace(".", "_")
            image.save(samples_dir / f"sample_{label}.png", compress_level=1)
        return

    for frame_idx in range(FRAME_COUNT):
        image = render_frame(frame_idx)
        image.save(frames_dir / f"frame_{frame_idx:05d}.png", compress_level=1)

    audio = build_audio(DURATION)
    write_wav(workdir / "audio.wav", audio)
    (workdir / "render-metadata.txt").write_text(
        f"fps={FPS}\nduration={DURATION}\nframes={FRAME_COUNT}\nresolution={WIDTH}x{HEIGHT}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
