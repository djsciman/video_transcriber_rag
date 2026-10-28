"""Find frames whose corner pixel is a compressed version of a given color.

Exact hex matches do not survive this encode. Volume 1 is 720p H.264 4:2:0
with no color tags, and a single pixel of a flat plate comes back a few
levels off. Decoding as BT.709 (limited range in, full range out) keeps the
hue. The lighter title cards are the same hue and saturation as the dark
ones, with value shifted by up to about 0.09. An RGB distance tight enough
for the dark plate misses those cards.

The match is therefore in HSV, relative to the hex you pass in:

  hue within --hue degrees (default 8; the plates here were within 5)
  saturation within --sat (default 0.08; the plates were within 0.05)
  value within --val (default 0.10; the lighter plates were within 0.09)

The first matching frame is printed. Further matches are ignored until
--gap seconds have passed (default 10).
"""

import argparse
import colorsys
import shutil
import subprocess
import sys


def parse_hex(text):
    raw = text.strip().lower()
    if raw.startswith("#"):
        raw = raw[1:]
    elif raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) != 6 or any(c not in "0123456789abcdef" for c in raw):
        raise argparse.ArgumentTypeError(f"expected RRGGBB hex, got {text!r}")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def frame_rate(video):
    probe = shutil.which("ffprobe")
    if probe is None:
        sys.exit("ffprobe not found on PATH")
    out = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate,r_frame_rate",
            "-of",
            "csv=p=0",
            video,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    if not out:
        sys.exit("ffprobe returned no video stream")
    rates = [part for part in out[0].split(",") if part and part != "0/0"]
    for rate in rates:
        num, den = rate.split("/")
        den = float(den)
        if den:
            return float(num) / den
    sys.exit(f"could not read a frame rate from {out[0]!r}")


def hue_degrees(h_a, h_b):
    # colorsys hue is 0..1 around the wheel.
    delta = abs(h_a - h_b) * 360.0
    if delta > 180.0:
        delta = 360.0 - delta
    return delta


def matches(rgb, target_hsv, hue_tol, sat_tol, val_tol):
    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    th, ts, tv = target_hsv
    return (
        hue_degrees(h, th) <= hue_tol
        and abs(s - ts) <= sat_tol
        and abs(v - tv) <= val_tol
    )


def iter_pixel(video, x, y):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found on PATH")
    # scale applies the matrix. format=rgb24 then crop so a 1x1 sample is
    # not rounded away by 4:2:0 (that happens if you crop the YUV frame).
    graph = (
        "scale=in_range=tv:out_range=pc:"
        "in_color_matrix=bt709:out_color_matrix=bt709,"
        f"format=rgb24,crop=1:1:{x}:{y}"
    )
    proc = subprocess.Popen(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            video,
            "-an",
            "-vsync",
            "0",
            "-vf",
            graph,
            "-f",
            "rawvideo",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    while True:
        pixel = proc.stdout.read(3)
        if len(pixel) < 3:
            break
        yield pixel[0], pixel[1], pixel[2]
    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    code = proc.wait()
    if code != 0:
        sys.exit(f"ffmpeg exited {code}\n{stderr}")


def format_timestamp(seconds):
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    hours, rem = divmod(whole, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def scan(video, rgb, x, y, gap, hue_tol, sat_tol, val_tol):
    fps = frame_rate(video)
    target_hsv = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    last = None
    found = []
    for index, pixel in enumerate(iter_pixel(video, x, y)):
        if not matches(pixel, target_hsv, hue_tol, sat_tol, val_tol):
            continue
        timestamp = index / fps
        if last is not None and timestamp < last + gap:
            continue
        found.append((timestamp, pixel))
        last = timestamp
    return fps, found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="video file to scan")
    parser.add_argument(
        "color",
        type=parse_hex,
        help="target color as RRGGBB hex, with or without a leading #",
    )
    parser.add_argument("--x", type=int, default=5, help="pixel column, 0-based (default 5)")
    parser.add_argument("--y", type=int, default=5, help="pixel row, 0-based (default 5)")
    parser.add_argument(
        "--gap",
        type=float,
        default=10.0,
        help="minimum seconds between reported frames (default 10)",
    )
    parser.add_argument(
        "--hue",
        type=float,
        default=8.0,
        help="max hue difference in degrees (default 8)",
    )
    parser.add_argument(
        "--sat",
        type=float,
        default=0.08,
        help="max saturation difference, 0 to 1 (default 0.08)",
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.10,
        help="max value difference, 0 to 1 (default 0.10)",
    )
    args = parser.parse_args()
    if args.x < 0 or args.y < 0:
        sys.exit("--x and --y must be >= 0")
    if args.gap < 0:
        sys.exit("--gap must be >= 0")

    _fps, found = scan(
        args.video,
        args.color,
        args.x,
        args.y,
        args.gap,
        args.hue,
        args.sat,
        args.val,
    )
    for timestamp, pixel in found:
        print(f"{format_timestamp(timestamp)}  #{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}")
    if not found:
        print("no matches", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
