from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIO_OUTPUT_DIR = ROOT_DIR / "data" / "audio"
DEFAULT_SECTION_PAUSE_SECONDS = 0.6


class AudioGenerationError(Exception):
    pass


def _split_script_into_audio_sections(script_text: str) -> list[str]:
    sections: list[str] = []
    current_lines: list[str] = []

    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                sections.append("\n".join(current_lines))
                current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        sections.append("\n".join(current_lines))

    return sections or [script_text.strip()]


def _run_checked(command: list[str], **kwargs: Any) -> None:
    try:
        subprocess.run(command, capture_output=True, check=True, **kwargs)
    except FileNotFoundError as error:
        raise AudioGenerationError(str(error)) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        message = stderr or stdout or str(error)
        raise AudioGenerationError(message) from error


def _synthesize_script_wav(
    script_text: str,
    wav_path: Path,
    *,
    piper_command: str,
    ffmpeg_command: str,
    model_path: Path,
    section_pause_seconds: float,
) -> None:
    sections = _split_script_into_audio_sections(script_text)
    if len(sections) == 1:
        _run_checked(
            [piper_command, "--model", str(model_path), "--output_file", str(wav_path)],
            input=sections[0],
            text=True,
        )
        return

    with tempfile.TemporaryDirectory(prefix="podcast-audio-") as temp_dir:
        temp_path = Path(temp_dir)
        silence_path = temp_path / "silence.wav"
        concat_list_path = temp_path / "concat.txt"
        concat_output_path = temp_path / "combined.wav"
        concat_entries: list[str] = []

        for index, section_text in enumerate(sections):
            section_wav_path = temp_path / f"section-{index:03d}.wav"
            _run_checked(
                [piper_command, "--model", str(model_path), "--output_file", str(section_wav_path)],
                input=section_text,
                text=True,
            )
            concat_entries.append(f"file '{section_wav_path.as_posix()}'")

        _run_checked(
            [
                ffmpeg_command,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=22050:cl=mono",
                "-t",
                str(section_pause_seconds),
                str(silence_path),
            ],
            text=True,
        )

        interleaved_entries: list[str] = []
        for index, entry in enumerate(concat_entries):
            interleaved_entries.append(entry)
            if index < len(concat_entries) - 1:
                interleaved_entries.append(f"file '{silence_path.as_posix()}'")

        concat_list_path.write_text("\n".join(interleaved_entries) + "\n", encoding="utf-8")
        _run_checked(
            [
                ffmpeg_command,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_path),
                "-c",
                "copy",
                str(concat_output_path),
            ],
            text=True,
        )
        shutil.copyfile(concat_output_path, wav_path)


def _resolve_command(command_name: str, env_name: str) -> str:
    configured_command = os.getenv(env_name, command_name).strip()
    resolved_command = shutil.which(configured_command)
    if not resolved_command:
        raise AudioGenerationError(f"Missing executable for {env_name}: {configured_command}")
    return resolved_command


def _resolve_model_path() -> Path:
    model_path = os.getenv("PODCAST_PIPER_MODEL_PATH", "").strip()
    if not model_path:
        raise AudioGenerationError("Missing Piper model path: set PODCAST_PIPER_MODEL_PATH")
    resolved = Path(model_path)
    if not resolved.exists():
        raise AudioGenerationError(f"Piper model not found: {resolved}")
    return resolved


def generate_local_mp3(
    script_text: str,
    job_id: str,
    *,
    category_pause_seconds: float = DEFAULT_SECTION_PAUSE_SECONDS,
) -> dict[str, Any]:
    if not script_text.strip():
        raise AudioGenerationError("Script text is empty")

    resolved_pause_seconds = max(0.0, float(category_pause_seconds))

    piper_command = _resolve_command("piper", "PODCAST_PIPER_COMMAND")
    ffmpeg_command = _resolve_command("ffmpeg", "PODCAST_FFMPEG_COMMAND")
    model_path = _resolve_model_path()

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = AUDIO_OUTPUT_DIR / f"{job_id}.wav"
    mp3_path = AUDIO_OUTPUT_DIR / f"{job_id}.mp3"
    if wav_path.exists():
        wav_path.unlink()
    if mp3_path.exists():
        mp3_path.unlink()

    try:
        _synthesize_script_wav(
            script_text,
            wav_path,
            piper_command=piper_command,
            ffmpeg_command=ffmpeg_command,
            model_path=model_path,
            section_pause_seconds=resolved_pause_seconds,
        )
        _run_checked(
            [ffmpeg_command, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "4", str(mp3_path)],
            text=True,
        )
    finally:
        if wav_path.exists():
            try:
                wav_path.unlink()
            except OSError:
                pass

    if not mp3_path.exists():
        raise AudioGenerationError("MP3 output was not created")

    return {
        "audio_file_name": mp3_path.name,
        "audio_download_url": f"/api/generation-jobs/{job_id}/audio",
        "audio_format": "mp3",
        "audio_mode_used": "local",
    }
