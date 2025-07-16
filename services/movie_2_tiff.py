"""
movie2tiff.py – TemI movie → per-frame TIFF extractor with focus scoring
========================================================================

This version extracts **every frame** from a proprietary *TemI* movie, saves
each frame to an individual TIFF, and returns the filename list **plus a per-
frame focus score**.  Filenames are based on a *stub* that you supply (or the
movies own name if you leave it blank).

Focus score algorithm
---------------------
A simple, fast, no-dependency metric:
* **Variance of the Laplacian** high-frequency content indicates sharp focus.
  For an NxM grayscale image *I* the discrete Laplacian is approximated by
  
  $$ \nabla^2 I = -4I_{i,j} + I_{i-1,j}+I_{i+1,j}+I_{i,j-1}+I_{i,j+1} $$
  and the focus score is the population variance of that response.

No OpenCV/SciPy needed – implemented with NumPy slicing.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Tuple

import numpy as np
from PIL import Image, TiffImagePlugin

# ---------------------------------------------------------------------------
# TemI constants (from movie2tiff_v2.c)
# ---------------------------------------------------------------------------
CAMERA_MOVIE_MAGIC = 0x496D6554  # 'TemI' little-endian
CAMERA_HEADER_LEN = 56

CAMERA_PIXELFORMAT_MONO_8 = 0x01080001
CAMERA_PIXELFORMAT_MONO_12_PACKED = 0x010C0006
CAMERA_PIXELFORMAT_MONO_16 = 0x01100007
CAMERA_PIXELFORMAT_MONO_32 = 0x01200111

G_BIG_ENDIAN = 4321
G_LITTLE_ENDIAN = 1234

_LOSSLESS_TIFF = {"raw", "tiff_lzw", "tiff_zip", "tiff_adobe_deflate"}

TAG_IMAGE_DESCRIPTION = 270  # ASCII/UTF-8 – JSON header dump
TAG_DATETIME = 306           # "YYYY:MM:DD HH:MM:SS"


# ---------------------------------------------------------------------------
# Header helper – mirrors `camera_save_struct` (version ≥ 2)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class FrameHeader:
    magic: int
    version: int
    type: int
    pixelformat: int
    length_header: int
    length_data: int
    endianness: int
    time_sec: int
    time_nsec: int
    width: int
    height: int
    stride: int

    _STRUCT = struct.Struct("<7I2Q3I")

    @classmethod
    def from_bytes(cls, buf: bytes) -> "FrameHeader":
        if len(buf) < CAMERA_HEADER_LEN:
            raise ValueError("Incomplete camera_save_struct header")
        fields = cls._STRUCT.unpack_from(buf)
        hdr = cls(*fields)
        if hdr.magic != CAMERA_MOVIE_MAGIC:
            raise ValueError("Bad TemI magic")
        return hdr

    # Convenience ----------------------------------------------------------
    @property
    def shape(self) -> Tuple[int, int]:
        return self.height, self.width

    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.time_sec + self.time_nsec / 1e9, tz=timezone.utc)

    def to_json(self, extra: bytes | None = None) -> str:
        d = {
            "magic": f"0x{self.magic:08X}",
            "version": self.version,
            "type": self.type,
            "pixelformat": f"0x{self.pixelformat:08X}",
            "length_header": self.length_header,
            "length_data": self.length_data,
            "endianness": self.endianness,
            "time_sec": self.time_sec,
            "time_nsec": self.time_nsec,
            "width": self.width,
            "height": self.height,
            "stride": self.stride,
        }
        if extra:
            d["extra_header_hex"] = extra.hex()
        return json.dumps(d, indent=2)


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------
class Movie2Tiff:
    """Extract every frame from a TemI movie to TIFF and return focus scores."""

    def __init__(self, compression: str = "tiff_lzw") -> None:
        compression = compression.lower()
        if compression not in _LOSSLESS_TIFF:
            raise ValueError(
                f"Unsupported compression '{compression}'. Choose from {', '.join(sorted(_LOSSLESS_TIFF))}")
        self.compression = compression

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def convert(
        self,
        movie_name: str | Path,
        file_stub: str | Path | None = None,
    ) -> Tuple[List[Path], List[float]]:
        """Process **all** frames and return filenames + focus scores.

        Parameters
        ----------
        movie_name : path-like
            TemI movie file.
        file_stub : str or path-like or ``None``
            Base name for output files – if ``None`` or empty, the movie’s
            *stem* is used.  For example, movie `clip.temi` → `clip_0001.tif`,
            `clip_0002.tif`, …

        Returns
        -------
        (list[Path], list[float])
            *Absolute* paths of written TIFFs and their corresponding focus
            scores (same order).
        """
        movie_p = Path(movie_name)
        if not movie_p.exists():
            raise FileNotFoundError(movie_p)

        # Determine stub path
        if not file_stub:
            stub_p = movie_p.with_suffix("")  # removes .temi, keeps dir
        else:
            stub_p = Path(file_stub).expanduser().resolve()
        # Directory: use stub's parent (or movie's if stub has no parent)
        out_dir = stub_p.parent if stub_p.parent != Path("") else movie_p.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        data = movie_p.read_bytes()
        frames = list(self._iterate_frames(data))
        n_frames = len(frames)
        if n_frames == 0:
            raise ValueError("No TemI frames found")

        width_pad = len(str(n_frames))
        filenames: List[Path] = []
        scores: List[float] = []

        for idx, (hdr, extra, mv) in enumerate(frames, start=1):
            arr = self._decode_frame(hdr, mv)
            score = self._calculate_focus_score(arr)
            scores.append(score)

            out_name = f"{stub_p.stem}_{idx:0{width_pad}d}.tiff"
            out_path = out_dir / out_name
            self._save_tiff(arr, out_path, hdr, extra, score)
            filenames.append(out_path.resolve())

        return filenames, scores

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _iterate_frames(data: bytes) -> Iterator[Tuple[FrameHeader, bytes, memoryview]]:
        magic = CAMERA_MOVIE_MAGIC.to_bytes(4, "little")
        off = 0
        total = len(data)
        while off < total:
            idx = data.find(magic, off)
            if idx == -1:
                break
            hdr = FrameHeader.from_bytes(data[idx : idx + CAMERA_HEADER_LEN])
            extra_start = idx + CAMERA_HEADER_LEN
            extra_end = idx + hdr.length_header
            extra = data[extra_start:extra_end]
            frame_start = extra_end
            frame_end = frame_start + hdr.length_data
            yield hdr, extra, memoryview(data)[frame_start:frame_end]
            off = frame_end

    # -------------- Focus metric ---------------
    @staticmethod
    def _calculate_focus_score(arr: np.ndarray) -> float:
        """Variance of Laplacian – higher ⇒ sharper."""
        if arr.dtype != np.float64:
            img = arr.astype(np.float64)
        else:
            img = arr  # zero-copy
        # Exclude 1-pixel border to keep indexing simple
        lap = (
            -4 * img[1:-1, 1:-1]
            + img[:-2, 1:-1] + img[2:, 1:-1]
            + img[1:-1, :-2] + img[1:-1, 2:]
        )
        return float(np.var(lap))

    # -------------- Frame decoding -------------
    @staticmethod
    def _decode_frame(hdr: FrameHeader, buf: memoryview) -> np.ndarray:
        h, w = hdr.shape
        stride = hdr.stride

        if hdr.pixelformat == CAMERA_PIXELFORMAT_MONO_8:
            out = np.empty((h, w), dtype=np.uint8)
            for r in range(h):
                off = r * stride
                out[r] = np.frombuffer(buf[off : off + w], dtype=np.uint8, count=w)
            return out

        if hdr.pixelformat == CAMERA_PIXELFORMAT_MONO_16:
            out = np.empty((h, w), dtype=np.uint16)
            for r in range(h):
                off = r * stride
                row = np.frombuffer(buf[off : off + w * 2], dtype="<u2", count=w)
                if hdr.endianness == G_BIG_ENDIAN:
                    row = row.byteswap()
                out[r] = row
            return out

        if hdr.pixelformat == CAMERA_PIXELFORMAT_MONO_12_PACKED:
            out = np.empty((h, w), dtype=np.uint16)
            for r in range(h):
                off = r * stride
                packed = buf[off : off + ((w + 1) // 2) * 3]
                j = 0
                for c in range(0, w, 2):
                    b0, b1, b2 = packed[j : j + 3]
                    out[r, c] = b0 | ((b1 & 0x0F) << 8)
                    if c + 1 < w:
                        out[r, c + 1] = (b1 >> 4) | (b2 << 4)
                    j += 3
            return out

        if hdr.pixelformat == CAMERA_PIXELFORMAT_MONO_32:
            out = np.empty((h, w), dtype=np.uint32)
            for r in range(h):
                off = r * stride
                row = np.frombuffer(buf[off : off + w * 4], dtype="<u4", count=w)
                if hdr.endianness == G_BIG_ENDIAN:
                    row = row.byteswap()
                out[r] = row
            return out

        raise NotImplementedError(f"Unsupported pixel format 0x{hdr.pixelformat:08X}")

    # -------------- TIFF writing ---------------
    def _save_tiff(
        self,
        arr: np.ndarray,
        path: Path,
        hdr: FrameHeader,
        extra: bytes,
        focus_score: float,
    ) -> None:
        img = Image.fromarray(arr)
        try:
            ifd = TiffImagePlugin.ImageFileDirectory_v2()
        except AttributeError:
            ifd = TiffImagePlugin.ImageFileDirectory()

        meta_json = json.loads(hdr.to_json(extra))
        meta_json["focus_var_lap"] = focus_score
        ifd[TAG_IMAGE_DESCRIPTION] = json.dumps(meta_json, indent=2)
        ifd[TAG_DATETIME] = hdr.timestamp.strftime("%Y:%m:%d %H:%M:%S")

        img.save(
            str(path),
            format="TIFF",
            compression=None if self.compression == "raw" else self.compression,
            tiffinfo=ifd,
        )


# ---------------------------------------------------------------------------
# CLI entry (optional)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Extract every frame of a TemI movie to TIFFs with focus scores")
    p.add_argument("movie", help="TemI movie file")
    p.add_argument("stub", nargs="?", default="", help="Filename stub (default = movie stem)")
    p.add_argument("-c", "--compression", default="tiff_lzw", help="TIFF compression")
    args = p.parse_args()

    conv = Movie2Tiff(compression=args.compression)
    files, scores = conv.convert(args.movie, args.stub)
    for fp, sc in zip(files, scores):
        print(f"{fp.name}\tfocus={sc:.1f}")
