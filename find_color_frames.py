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
import threading


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


def video_size(video):
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
            "stream=width,height",
            "-of",
            "csv=p=0",
            video,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    if not out or "," not in out[0]:
        sys.exit("ffprobe returned no frame size")
    width, height = out[0].split(",")[:2]
    return int(width), int(height)


FRAME_GRAPH = (
    "scale=in_range=tv:out_range=pc:"
    "in_color_matrix=bt709:out_color_matrix=bt709,"
    "format=rgb24"
)


def read_frame(video, seconds):
    """Return one RGB frame at `seconds`, using the same matrix as the scan."""
    numpy = _numpy()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found on PATH")
    width, height = video_size(video)
    proc = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            video,
            "-frames:v",
            "1",
            "-an",
            "-vf",
            FRAME_GRAPH,
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
    )
    raw = proc.stdout
    if proc.returncode != 0 or len(raw) < width * height * 3:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        sys.exit(f"could not read a frame at {seconds:.3f}s\n{detail}")
    frame = numpy.frombuffer(raw, dtype=numpy.uint8)[: width * height * 3]
    return frame.reshape(height, width, 3).copy()


def iter_frames(video):
    """Yield each frame as an HxWx3 uint8 array, same matrix as iter_pixel."""
    numpy = _numpy()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found on PATH")
    width, height = video_size(video)
    graph = FRAME_GRAPH
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
    errors = []

    def _read_errors():
        if proc.stderr is not None:
            errors.append(proc.stderr.read())

    reader = threading.Thread(target=_read_errors)
    reader.start()
    nbytes = width * height * 3
    while True:
        raw = proc.stdout.read(nbytes)
        if len(raw) < nbytes:
            break
        frame = numpy.frombuffer(raw, dtype=numpy.uint8).reshape(height, width, 3)
        yield frame
    reader.join()
    code = proc.wait()
    if code != 0:
        stderr = errors[0].decode("utf-8", "replace") if errors else ""
        sys.exit(f"ffmpeg exited {code}\n{stderr}")


def _numpy():
    try:
        import numpy
    except ImportError:
        sys.exit("numpy is required to count matching pixels")
    return numpy


def _cv2():
    try:
        import cv2
    except ImportError:
        sys.exit("opencv-python is required to count matching pixels")
    return cv2


def tolerance_ranges(target_hsv, hue_tol, sat_tol, val_tol):
    """OpenCV HSV bounds for inRange. Hue wraps into two ranges at red.

    OpenCV stores hue as degrees/2 (0..179) and saturation and value as
    0..255. The bounds use the same hue, saturation, and value tolerances
    as matches().
    """
    numpy = _numpy()
    hue, saturation, value = target_hsv
    hue_cv = hue * 180.0
    sat_cv = saturation * 255.0
    val_cv = value * 255.0
    sat_lo = max(0, int(numpy.floor(sat_cv - sat_tol * 255.0)))
    sat_hi = min(255, int(numpy.ceil(sat_cv + sat_tol * 255.0)))
    val_lo = max(0, int(numpy.floor(val_cv - val_tol * 255.0)))
    val_hi = min(255, int(numpy.ceil(val_cv + val_tol * 255.0)))
    start = hue_cv - hue_tol / 2.0
    end = hue_cv + hue_tol / 2.0
    if start < 0:
        spans = [(0.0, end), (180.0 + start, 179.0)]
    elif end > 179.0:
        spans = [(start, 179.0), (0.0, end - 180.0)]
    else:
        spans = [(start, end)]
    ranges = []
    for span_start, span_end in spans:
        hue_lo = max(0, int(numpy.floor(span_start)))
        hue_hi = min(179, int(numpy.ceil(span_end)))
        ranges.append(
            (
                numpy.array((hue_lo, sat_lo, val_lo), dtype=numpy.uint8),
                numpy.array((hue_hi, sat_hi, val_hi), dtype=numpy.uint8),
            )
        )
    return ranges


def match_count(frame, ranges):
    """Count pixels inside the HSV tolerance ranges."""
    cv2 = _cv2()
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    count = 0
    for low, high in ranges:
        count += cv2.countNonZero(cv2.inRange(hsv, low, high))
    return count


def _median_rgb(pixels):
    """Per-channel median of an (N, 3) or (H, W, 3) array."""
    numpy = _numpy()
    flat = pixels.reshape(-1, 3)
    median = numpy.median(flat, axis=0)
    return tuple(int(numpy.clip(numpy.round(channel), 0, 255)) for channel in median)


def _coverage(frame, rgb, hue_tol, sat_tol, val_tol):
    target = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    ranges = tolerance_ranges(target, hue_tol, sat_tol, val_tol)
    total = frame.shape[0] * frame.shape[1]
    return match_count(frame, ranges) / total


def _hsv_cv_to_rgb(hue_cv, sat_cv, val_cv):
    red, green, blue = colorsys.hsv_to_rgb(
        (hue_cv / 180.0) % 1.0,
        min(1.0, sat_cv / 255.0),
        min(1.0, val_cv / 255.0),
    )
    return (
        int(round(red * 255)),
        int(round(green * 255)),
        int(round(blue * 255)),
    )


def _bin_rgb(hue_i, sat_i, val_i, hue_step, sat_step, val_step):
    return _hsv_cv_to_rgb(
        min(179.0, (hue_i + 0.5) * hue_step),
        min(255.0, (sat_i + 0.5) * sat_step),
        min(255.0, (val_i + 0.5) * val_step),
    )


def _refine_rgb(frame, rgb, share, hue_tol, sat_tol, val_tol):
    """Move `rgb` to the median of the pixels it already matches."""
    numpy = _numpy()
    cv2 = _cv2()
    target = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    ranges = tolerance_ranges(target, hue_tol, sat_tol, val_tol)
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    mask = numpy.zeros(frame.shape[:2], dtype=numpy.uint8)
    for low, high in ranges:
        mask = numpy.maximum(mask, cv2.inRange(hsv, low, high))
    if int(mask.sum()) == 0:
        return rgb, share
    refined = _median_rgb(frame[mask > 0])
    refined_share = _coverage(frame, refined, hue_tol, sat_tol, val_tol)
    if refined_share >= share:
        return refined, refined_share
    return rgb, share


def dominant_rgb(frame, hue_tol, sat_tol, val_tol):
    """Return (rgb, coverage) for the tolerance ball that covers the most pixels.

    Candidate centers are the fullest HSV bins. Each is scored with the
    same tolerance the scanner uses, and the winner is moved to the median
    of the pixels inside its ball when that covers at least as much.
    """
    numpy = _numpy()
    cv2 = _cv2()
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    hue_step, sat_step, val_step = 2, 8, 8
    hue_bins = 180 // hue_step
    sat_bins = (256 + sat_step - 1) // sat_step
    val_bins = (256 + val_step - 1) // val_step
    hue_bin = numpy.clip(hsv[:, :, 0].astype(numpy.int32) // hue_step, 0, hue_bins - 1)
    sat_bin = numpy.clip(hsv[:, :, 1].astype(numpy.int32) // sat_step, 0, sat_bins - 1)
    val_bin = numpy.clip(hsv[:, :, 2].astype(numpy.int32) // val_step, 0, val_bins - 1)
    hist = numpy.zeros((hue_bins, sat_bins, val_bins), dtype=numpy.int32)
    numpy.add.at(hist, (hue_bin.ravel(), sat_bin.ravel(), val_bin.ravel()), 1)
    occupied = numpy.argwhere(hist > 0)
    counts = hist[occupied[:, 0], occupied[:, 1], occupied[:, 2]]
    order = numpy.argsort(-counts)[:24]
    # Score on a stride so a few dozen candidates stay cheap. The winner
    # is measured again on the full frame.
    small = frame[::4, ::4]
    best_rgb = None
    best_share = -1.0
    for index in order:
        hue_i, sat_i, val_i = (int(part) for part in occupied[index])
        rgb = _bin_rgb(hue_i, sat_i, val_i, hue_step, sat_step, val_step)
        share = _coverage(small, rgb, hue_tol, sat_tol, val_tol)
        if share > best_share:
            best_rgb = rgb
            best_share = share
    share = _coverage(frame, best_rgb, hue_tol, sat_tol, val_tol)
    return _refine_rgb(frame, best_rgb, share, hue_tol, sat_tol, val_tol)


def predominant_color(frames, hue_tol, sat_tol, val_tol, minimum):
    """Pick the plate color with the highest worst-frame coverage.

    Each sample's dominant color is a candidate. A blend of those colors
    is not: two different plates average to a third color that matches
    neither frame. `minimum` is the coverage the caller requires; this
    still returns the best candidate when every frame is under it.
    """
    del minimum
    candidates = []
    for frame in frames:
        rgb, _share = dominant_rgb(frame, hue_tol, sat_tol, val_tol)
        if rgb not in candidates:
            candidates.append(rgb)
    best = None
    best_worst = -1.0
    best_coverages = None
    for rgb in candidates:
        coverages = [_coverage(frame, rgb, hue_tol, sat_tol, val_tol) for frame in frames]
        worst = min(coverages)
        if worst > best_worst:
            best = rgb
            best_worst = worst
            best_coverages = coverages
    return best, best_coverages


# Fallback when one hex color stays under the fraction threshold.
# A dark saturated graphic passes. A bright mat and a gray slate do not.
DARK_SAT_MIN = 0.5
DARK_VAL_MAX = 0.45


def dark_saturated_bounds(sat_min=DARK_SAT_MIN, val_max=DARK_VAL_MAX):
    """OpenCV HSV bounds for saturation above `sat_min` and value below `val_max`."""
    numpy = _numpy()
    sat_lo = min(255, int(numpy.floor(sat_min * 255.0)) + 1)
    val_hi = max(0, int(numpy.ceil(val_max * 255.0)) - 1)
    return (
        numpy.array((0, sat_lo, 0), dtype=numpy.uint8),
        numpy.array((179, 255, val_hi), dtype=numpy.uint8),
    )


def dark_saturated_count(frame, bounds=None):
    """Count pixels that are saturated and dark. Hue is ignored."""
    cv2 = _cv2()
    if bounds is None:
        bounds = dark_saturated_bounds()
    low, high = bounds
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    return cv2.countNonZero(cv2.inRange(hsv, low, high))


def dark_saturated_share(frame, bounds=None):
    total = frame.shape[0] * frame.shape[1]
    return dark_saturated_count(frame, bounds) / total


def _scan(video, gap, minimum, count_frame):
    """Return (fps, [(timestamp, fraction), ...]).

    A frame counts when `count_frame` is strictly greater than `minimum`
    times the pixel count. Further frames are ignored until `gap` seconds pass.
    """
    fps = frame_rate(video)
    last = None
    found = []
    total = None
    for index, frame in enumerate(iter_frames(video)):
        if total is None:
            total = frame.shape[0] * frame.shape[1]
        count = count_frame(frame)
        if count <= minimum * total:
            continue
        timestamp = index / fps
        if last is not None and timestamp < last + gap:
            continue
        found.append((timestamp, count / total))
        last = timestamp
    return fps, found


def scan_frames(video, rgb, gap, hue_tol, sat_tol, val_tol, minimum):
    """Return (fps, [(timestamp, fraction), ...]) for one hex plate color."""
    target_hsv = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    ranges = tolerance_ranges(target_hsv, hue_tol, sat_tol, val_tol)
    return _scan(video, gap, minimum, lambda frame: match_count(frame, ranges))


def scan_dark_saturated(video, gap, minimum, sat_min=DARK_SAT_MIN, val_max=DARK_VAL_MAX):
    """Return (fps, [(timestamp, fraction), ...]) for dark saturated pixels."""
    bounds = dark_saturated_bounds(sat_min, val_max)
    return _scan(video, gap, minimum, lambda frame: dark_saturated_count(frame, bounds))


# One frame a second is enough to see a title card that stays up for several seconds.
AUTO_SAMPLE_SECONDS = 1.0
AUTO_SAMPLE_WIDTH = 320
# The lesson cluster and a card cluster must be at least this far apart.
AUTO_SCORE_GAP = 0.15
AUTO_BIN_WIDTH = 0.02
# Cards are a small part of the file. A wider high cluster is the lesson.
AUTO_MAX_CARD_FRACTION = 0.20
# A spike shorter than this does not open a chapter.
AUTO_HOLD_SECONDS = 0.5


def anomalous_threshold(scores, gap=AUTO_SCORE_GAP, max_fraction=AUTO_MAX_CARD_FRACTION, bin_width=AUTO_BIN_WIDTH):
    """Return a cut for a rare high cluster, or None when the scores are one hump.

    The dense low cluster is the lesson. A card cluster sits at least `gap`
    above it and holds at most `max_fraction` of the samples. The cut is the
    midpoint of that empty stretch.
    """
    numpy = _numpy()
    values = numpy.asarray(scores, dtype=numpy.float64)
    if values.size < 8:
        return None
    edges = numpy.arange(0.0, 1.0 + bin_width, bin_width)
    counts, edges = numpy.histogram(values, bins=edges)
    mode = int(numpy.argmax(counts))
    occupied = counts >= 2
    gap_bins = int(numpy.ceil(gap / bin_width))
    last_body = mode
    empty_run = 0
    for index in range(mode + 1, len(counts)):
        if occupied[index]:
            last_body = index
            empty_run = 0
            continue
        empty_run += 1
        if empty_run >= gap_bins:
            break
    high_indexes = [
        index for index in range(last_body + 1, len(counts))
        if occupied[index] and index - last_body >= gap_bins
    ]
    if not high_indexes:
        return None
    normal_hi = float(edges[last_body + 1])
    high_lo = float(edges[high_indexes[0]])
    if high_lo - normal_hi < gap:
        return None
    high = values[values >= high_lo]
    if high.size < 2 or high.size / values.size > max_fraction:
        return None
    return (normal_hi + high_lo) / 2.0


def _scaled_size(video, width):
    src_w, src_h = video_size(video)
    scaled_w = min(width, src_w)
    scaled_h = int(round(src_h * scaled_w / src_w))
    scaled_h -= scaled_h % 2
    if scaled_h < 2:
        scaled_h = 2
    return scaled_w, scaled_h


def score_timeline(video, hue_tol, sat_tol, val_tol, step=AUTO_SAMPLE_SECONDS, on_sample=None):
    """Return (timestamp, dark share, dominant-color share, rgb) once per `step` seconds."""
    numpy = _numpy()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found on PATH")
    width, height = _scaled_size(video, AUTO_SAMPLE_WIDTH)
    graph = f"fps=1/{step:g},scale={width}:{height},{FRAME_GRAPH}"
    proc = subprocess.Popen(
        [ffmpeg, "-v", "error", "-i", video, "-an", "-vf", graph, "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    errors = []

    def _read_errors():
        if proc.stderr is not None:
            errors.append(proc.stderr.read())

    reader = threading.Thread(target=_read_errors)
    reader.start()
    nbytes = width * height * 3
    rows = []
    index = 0
    while True:
        raw = proc.stdout.read(nbytes)
        if len(raw) < nbytes:
            break
        frame = numpy.frombuffer(raw, dtype=numpy.uint8, count=nbytes).reshape(height, width, 3).copy()
        dark = dark_saturated_share(frame)
        rgb, share = dominant_rgb(frame, hue_tol, sat_tol, val_tol)
        timestamp = index * step
        rows.append((timestamp, dark, share, rgb))
        if on_sample is not None:
            on_sample(timestamp)
        index += 1
    reader.join()
    code = proc.wait()
    if code != 0:
        stderr = errors[0].decode("utf-8", "replace") if errors else ""
        sys.exit(f"ffmpeg exited {code}\n{stderr}")
    return rows


def cluster_plates(rgbs, hue_tol, sat_tol, val_tol):
    """Group dominant colors that sit inside one HSV tolerance."""
    numpy = _numpy()
    clusters = []
    for rgb in rgbs:
        placed = False
        for cluster in clusters:
            center = _median_rgb(numpy.array(cluster, dtype=numpy.float64))
            target = colorsys.rgb_to_hsv(center[0] / 255.0, center[1] / 255.0, center[2] / 255.0)
            if matches(rgb, target, hue_tol, sat_tol, val_tol):
                cluster.append(rgb)
                placed = True
                break
        if not placed:
            clusters.append([list(rgb)])
    plates = []
    for cluster in clusters:
        plates.append(_median_rgb(numpy.array(cluster, dtype=numpy.float64)))
    return plates


def auto_spec(rows, hue_tol, sat_tol, val_tol):
    """Return the dark cut and plate colors whose scores form a high cluster."""
    dark_cut = anomalous_threshold([row[1] for row in rows])
    color_cut = anomalous_threshold([row[2] for row in rows])
    plates = []
    if color_cut is not None:
        high_rgbs = [row[3] for row in rows if row[2] >= color_cut]
        for rgb in cluster_plates(high_rgbs, hue_tol, sat_tol, val_tol):
            target = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
            plates.append((rgb, color_cut, tolerance_ranges(target, hue_tol, sat_tol, val_tol)))
    if dark_cut is None and not plates:
        return None
    return {
        "dark_cut": dark_cut,
        "dark_bounds": dark_saturated_bounds() if dark_cut is not None else None,
        "plates": plates,
    }


def auto_match(frame, spec):
    """Return (matched, share) for a frame against an auto spec."""
    total = frame.shape[0] * frame.shape[1]
    best = 0.0
    matched = False
    dark_cut = spec["dark_cut"]
    if dark_cut is not None:
        share = dark_saturated_count(frame, spec["dark_bounds"]) / total
        if share > dark_cut:
            matched = True
            best = share
    for _rgb, cut, ranges in spec["plates"]:
        share = match_count(frame, ranges) / total
        if share > cut:
            matched = True
            if share > best:
                best = share
    return matched, best


def scan_auto(video, gap, spec, hold=AUTO_HOLD_SECONDS):
    """Return (fps, [(timestamp, fraction), ...]) for histogram cards.

    A run has to stay matched for `hold` seconds. The chapter opens at the
    first frame of that run. Further runs are ignored until `gap` seconds
    after that start.
    """
    fps = frame_rate(video)
    run_start = None
    emitted = False
    last_emit = None
    found = []
    for index, frame in enumerate(iter_frames(video)):
        timestamp = index / fps
        matched, share = auto_match(frame, spec)
        if matched:
            if run_start is None:
                run_start = timestamp
                emitted = False
            if not emitted and timestamp - run_start >= hold - (0.5 / fps):
                if last_emit is None or run_start >= last_emit + gap:
                    found.append((run_start, share))
                    last_emit = run_start
                emitted = True
            continue
        run_start = None
        emitted = False
    return fps, found


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
