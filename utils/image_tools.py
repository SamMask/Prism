# -*- coding: utf-8 -*-
"""Image helpers that keep Prism's Python runtime free of Pillow."""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"


def generate_webp_thumbnail(source_path: str, output_path: str, timeout: int = 120) -> bool:
    """Generate a Prism WebP thumbnail with the Go encoder helper."""
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file():
        return False

    output.parent.mkdir(parents=True, exist_ok=True)
    commands = _thumbnail_helper_commands(source, output)
    for cmd, cwd in commands:
        run_kwargs = {
            "cwd": str(cwd) if cwd else None,
            "text": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "timeout": timeout,
            "check": False,
        }
        if os.name == "nt":
            run_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(cmd, **run_kwargs)
        except (OSError, subprocess.TimeoutExpired) as exc:
            _cleanup_partial(output)
            print(f"[Warning] Go thumbnail helper failed to start: {exc}")
            continue

        if result.returncode == 0 and output.is_file() and output.stat().st_size > 0:
            return True

        _cleanup_partial(output)
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            print(f"[Warning] Go thumbnail helper failed: {detail}")

    return False


def thumbnail_name(filename: str) -> str:
    return f"{Path(filename).stem}_thumb.webp"


def extract_prompt_metadata(file_path: str) -> dict:
    """Extract known prompt metadata without Pillow.

    Supports PNG tEXt/zTXt/iTXt fields used by Stable Diffusion, ComfyUI, and
    NovelAI, plus a small JPEG EXIF UserComment reader.
    """
    path = Path(file_path)
    metadata = _read_png_text(path)
    if not metadata:
        user_comment = _read_jpeg_user_comment(path)
        metadata = {"UserComment": user_comment} if user_comment else {}

    return _prompt_data_from_metadata(metadata)


def _thumbnail_helper_commands(source: Path, output: Path) -> list[tuple[list[str], Optional[Path]]]:
    args = ["--thumbnail-input", str(source), "--thumbnail-output", str(output)]
    commands: list[tuple[list[str], Optional[Path]]] = []

    env_helper = os.environ.get("PRISM_GO_THUMBNAIL_HELPER")
    if env_helper:
        commands.append(([env_helper, *args], None))

    exe_name = "prism-go-runtime.exe" if os.name == "nt" else "prism-go-runtime"
    closure_exe_name = "prism-go-runtime-pillow-closure.exe" if os.name == "nt" else "prism-go-runtime-pillow-closure"
    for candidate in (
        ROOT / "build" / "phase23-pillow-closure" / closure_exe_name,
        ROOT / "build" / "go-runtime" / exe_name,
        GO_SHADOW_DIR / exe_name,
    ):
        if candidate.is_file():
            commands.append(([str(candidate), *args], None))

    go_cmd = shutil.which("go")
    if go_cmd and GO_SHADOW_DIR.is_dir():
        commands.append(([go_cmd, "run", ".", *args], GO_SHADOW_DIR))

    return commands


def _cleanup_partial(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _read_png_text(path: Path) -> dict[str, str]:
    try:
        data = path.read_bytes()
    except OSError:
        return {}

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return {}

    offset = 8
    fields: dict[str, str] = {}
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(data):
            break
        chunk = data[chunk_start:chunk_end]

        if chunk_type == b"tEXt":
            parsed = _parse_text_chunk(chunk)
            if parsed:
                fields[parsed[0]] = parsed[1]
        elif chunk_type == b"zTXt":
            parsed = _parse_ztxt_chunk(chunk)
            if parsed:
                fields[parsed[0]] = parsed[1]
        elif chunk_type == b"iTXt":
            parsed = _parse_itxt_chunk(chunk)
            if parsed:
                fields[parsed[0]] = parsed[1]
        elif chunk_type == b"IEND":
            break

        offset = chunk_end + 4

    return fields


def _parse_text_chunk(chunk: bytes) -> Optional[tuple[str, str]]:
    if b"\x00" not in chunk:
        return None
    keyword, text = chunk.split(b"\x00", 1)
    return _decode_latin1(keyword), _decode_text(text)


def _parse_ztxt_chunk(chunk: bytes) -> Optional[tuple[str, str]]:
    parts = chunk.split(b"\x00", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    keyword, rest = parts
    compression_method = rest[0]
    if compression_method != 0:
        return None
    try:
        text = zlib.decompress(rest[1:])
    except zlib.error:
        return None
    return _decode_latin1(keyword), _decode_text(text)


def _parse_itxt_chunk(chunk: bytes) -> Optional[tuple[str, str]]:
    parts = chunk.split(b"\x00", 5)
    if len(parts) != 6:
        return None
    keyword, compression_flag, compression_method, _language, _translated, text = parts
    if compression_flag == b"\x01":
        if compression_method != b"\x00":
            return None
        try:
            text = zlib.decompress(text)
        except zlib.error:
            return None
    return _decode_latin1(keyword), _decode_text(text)


def _read_jpeg_user_comment(path: Path) -> Optional[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.startswith(b"\xff\xd8"):
        return None

    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            break
        marker = data[offset + 1]
        offset += 2
        if marker in (0xD8, 0xD9):
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        segment = data[offset + 2 : offset + segment_length]
        offset += segment_length

        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
            return _read_exif_user_comment(segment[6:])
    return None


def _read_exif_user_comment(tiff: bytes) -> Optional[str]:
    if len(tiff) < 8:
        return None
    endian = "<" if tiff[:2] == b"II" else ">" if tiff[:2] == b"MM" else ""
    if not endian or _unpack(endian, "H", tiff, 2) != 42:
        return None

    ifd0 = _unpack(endian, "I", tiff, 4)
    exif_ifd = _find_tiff_tag(tiff, endian, ifd0, 0x8769)
    if exif_ifd is None:
        return None
    raw = _find_tiff_tag(tiff, endian, exif_ifd, 0x9286)
    if raw is None:
        return None
    if isinstance(raw, int):
        return None
    return _decode_user_comment(raw)


def _find_tiff_tag(tiff: bytes, endian: str, ifd_offset: int, tag_id: int):
    if ifd_offset < 0 or ifd_offset + 2 > len(tiff):
        return None
    count = _unpack(endian, "H", tiff, ifd_offset)
    entries = ifd_offset + 2
    for index in range(count):
        entry = entries + index * 12
        if entry + 12 > len(tiff):
            return None
        tag = _unpack(endian, "H", tiff, entry)
        field_type = _unpack(endian, "H", tiff, entry + 2)
        value_count = _unpack(endian, "I", tiff, entry + 4)
        value_or_offset = tiff[entry + 8 : entry + 12]
        if tag != tag_id:
            continue
        byte_count = _tiff_byte_count(field_type, value_count)
        if byte_count <= 0:
            return None
        if byte_count <= 4:
            raw = value_or_offset[:byte_count]
        else:
            value_offset = _unpack(endian, "I", tiff, entry + 8)
            raw = tiff[value_offset : value_offset + byte_count]
        if field_type in (3, 4) and byte_count <= 4:
            return _unpack(endian, "I" if field_type == 4 else "H", raw + b"\x00" * 4, 0)
        return raw
    return None


def _tiff_byte_count(field_type: int, count: int) -> int:
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 7: 1}
    return sizes.get(field_type, 0) * count


def _unpack(endian: str, fmt: str, data: bytes, offset: int) -> int:
    return struct.unpack_from(endian + fmt, data, offset)[0]


def _prompt_data_from_metadata(info: dict[str, str]) -> dict:
    prompt_data = {
        "prompt": None,
        "negative_prompt": None,
        "source": None,
        "raw_metadata": None,
    }

    if "parameters" in info:
        params = info["parameters"]
        prompt_data["raw_metadata"] = params
        prompt_data["source"] = "stable_diffusion"
        lines = params.split("\n")
        prompt_lines = []
        neg_prompt = None
        for line in lines:
            if line.startswith("Negative prompt:"):
                neg_prompt = line.replace("Negative prompt:", "", 1).strip()
            elif line.startswith(("Steps:", "Size:", "Sampler:")):
                break
            else:
                prompt_lines.append(line)
        prompt_data["prompt"] = "\n".join(prompt_lines).strip()
        prompt_data["negative_prompt"] = neg_prompt
    elif "prompt" in info:
        prompt_data["prompt"] = info["prompt"]
        prompt_data["source"] = "comfyui"
        prompt_data["raw_metadata"] = info["prompt"]
    elif "Comment" in info:
        prompt_data["raw_metadata"] = info["Comment"]
        try:
            comment = json.loads(info["Comment"])
            if "prompt" in comment:
                prompt_data["prompt"] = comment["prompt"]
                prompt_data["negative_prompt"] = comment.get("uc")
                prompt_data["source"] = "novelai"
        except Exception:
            pass
    elif "Description" in info:
        prompt_data["prompt"] = info["Description"]
        prompt_data["source"] = "description"
        prompt_data["raw_metadata"] = info["Description"]
    elif "UserComment" in info:
        prompt_data["prompt"] = info["UserComment"]
        prompt_data["source"] = "exif"
        prompt_data["raw_metadata"] = info["UserComment"]

    return prompt_data


def _decode_user_comment(raw: bytes) -> str:
    if raw.startswith(b"ASCII\x00\x00\x00"):
        raw = raw[8:]
    elif raw.startswith(b"UNICODE\x00"):
        raw = raw[8:]
        return raw.decode("utf-16-be", errors="ignore").rstrip("\x00")
    return _decode_text(raw).rstrip("\x00")


def _decode_latin1(data: bytes) -> str:
    return data.decode("latin-1", errors="replace")


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")
