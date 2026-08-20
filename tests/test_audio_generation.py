from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import repository
from app.db import ensure_database
from app.audio_generation import generate_local_mp3


ensure_database()


class AudioGenerationTests(unittest.TestCase):
    def test_generate_local_mp3_creates_downloadable_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "audio"
            model_path = Path(tmpdir) / "piper-model.onnx"
            model_path.write_text("model", encoding="utf-8")

            def fake_run(command, *, input=None, text=None, capture_output=None, check=None):
                target_path = Path(command[-1])
                if command[0] == "piper":
                    target_path.write_text("wave", encoding="utf-8")
                elif command[0] == "ffmpeg":
                    target_path.write_bytes(b"mp3")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with patch.dict(
                os.environ,
                {
                    "PODCAST_PIPER_MODEL_PATH": str(model_path),
                    "PODCAST_PIPER_COMMAND": "piper",
                    "PODCAST_FFMPEG_COMMAND": "ffmpeg",
                },
                clear=False,
            ), patch("app.audio_generation.AUDIO_OUTPUT_DIR", output_dir), patch(
                "app.audio_generation.shutil.which",
                side_effect=lambda command: command,
            ), patch("app.audio_generation.subprocess.run", side_effect=fake_run):
                result = generate_local_mp3("Bonjour tout le monde", "job-123")

            mp3_path = output_dir / "job-123.mp3"
            wav_path = output_dir / "job-123.wav"
            self.assertTrue(mp3_path.exists())
            self.assertFalse(wav_path.exists())
            self.assertEqual(result["audio_file_name"], "job-123.mp3")
            self.assertEqual(result["audio_download_url"], "/api/generation-jobs/job-123/audio")

    def test_generate_local_mp3_adds_pause_between_script_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "audio"
            model_path = Path(tmpdir) / "piper-model.onnx"
            model_path.write_text("model", encoding="utf-8")
            commands: list[list[str]] = []

            def fake_run(command, *, input=None, text=None, capture_output=None, check=None):
                commands.append(command)
                if command[0] == "piper":
                    Path(command[-1]).write_text(f"wave:{input}", encoding="utf-8")
                elif command[0] == "ffmpeg" and "anullsrc=r=22050:cl=mono" in command:
                    Path(command[-1]).write_text("silence", encoding="utf-8")
                elif command[0] == "ffmpeg" and "concat" in command:
                    Path(command[-1]).write_text("combined", encoding="utf-8")
                elif command[0] == "ffmpeg":
                    Path(command[-1]).write_bytes(b"mp3")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with patch.dict(
                os.environ,
                {
                    "PODCAST_PIPER_MODEL_PATH": str(model_path),
                    "PODCAST_PIPER_COMMAND": "piper",
                    "PODCAST_FFMPEG_COMMAND": "ffmpeg",
                },
                clear=False,
            ), patch("app.audio_generation.AUDIO_OUTPUT_DIR", output_dir), patch(
                "app.audio_generation.shutil.which",
                side_effect=lambda command: command,
            ), patch("app.audio_generation.subprocess.run", side_effect=fake_run):
                result = generate_local_mp3(
                    "Intro\n\nCategorie A\nSujet 1\n\nCategorie B\nSujet 2",
                    "job-456",
                    category_pause_seconds=1.2,
                )

            piper_calls = [command for command in commands if command[0] == "piper"]
            silence_calls = [command for command in commands if command[0] == "ffmpeg" and "anullsrc=r=22050:cl=mono" in command]
            self.assertEqual(len(piper_calls), 3)
            self.assertTrue(silence_calls)
            self.assertTrue(any(command[0] == "ffmpeg" and "concat" in command for command in commands))
            self.assertEqual(silence_calls[0][8], "1.2")
            self.assertEqual(result["audio_file_name"], "job-456.mp3")

    def test_audio_mode_persists_in_profile(self):
        profile = repository.get_or_create_default_profile()
        original_mode = repository.get_audio_generation_mode(profile["id"])
        try:
            updated = repository.update_audio_generation_mode(profile["id"], "cloud")
            self.assertIsNotNone(updated)
            self.assertEqual(repository.get_audio_generation_mode(profile["id"]), "cloud")
            self.assertEqual(updated["audio_generation_mode"], "cloud")
        finally:
            if original_mode:
                repository.update_audio_generation_mode(profile["id"], original_mode)


if __name__ == "__main__":
    unittest.main()
