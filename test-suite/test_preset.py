"""Unit tests for `app.services.preset` (service functions only)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from PIL import Image

from app.services.preset import (
    PresetBusyError,
    PresetFileMissingError,
    PresetJobLimiter,
    PresetNotFoundError,
    PresetPathUnsafeError,
    apply_named_preset,
    resolve_preset_file,
    run_preset_job,
)
from database.db_ops import add_preset
from database.init_db import init_db


def _make_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a mini repo with presets/ + empty DB; return (repo_root, db_path, presets_dir)."""
    repo_root = tmp_path / "repo"
    presets_dir = repo_root / "backend" / "presets"
    presets_dir.mkdir(parents=True)
    db_path = tmp_path / "presets.db"
    init_db(db_path)
    return repo_root, db_path, presets_dir


def _write_gray_preset(presets_dir: Path, name: str = "simple_gray") -> Path:
    preset_json = presets_dir / f"{name}.json"
    preset_json.write_text(
        json.dumps(
            {
                "name": name,
                "steps": [{"filter": "grayscale", "on": "image"}],
            }
        ),
        encoding="utf-8",
    )
    return preset_json


def test_resolve_preset_file_requires_name(tmp_path: Path) -> None:
    _, db_path, _ = _make_repo(tmp_path)
    with pytest.raises(ValueError, match="preset_name"):
        resolve_preset_file("  ", db_path=db_path)


def test_resolve_preset_file_missing_db_row(tmp_path: Path) -> None:
    repo_root, db_path, _ = _make_repo(tmp_path)
    with pytest.raises(PresetNotFoundError):
        resolve_preset_file("no_such_preset", db_path=db_path, repo_root=repo_root)


def test_resolve_preset_file_missing_json(tmp_path: Path) -> None:
    repo_root, db_path, _ = _make_repo(tmp_path)
    add_preset(
        "ghost",
        "backend/presets/ghost.json",
        db_path=db_path,
    )
    with pytest.raises(PresetFileMissingError):
        resolve_preset_file("ghost", db_path=db_path, repo_root=repo_root)


def test_resolve_preset_file_finds_under_repo_root(tmp_path: Path) -> None:
    repo_root, db_path, presets_dir = _make_repo(tmp_path)
    preset_json = _write_gray_preset(presets_dir)
    add_preset(
        "simple_gray",
        "backend/presets/simple_gray.json",
        db_path=db_path,
    )

    resolved = resolve_preset_file(
        "simple_gray",
        db_path=db_path,
        repo_root=repo_root,
    )
    assert resolved == preset_json.resolve()


def test_resolve_preset_file_rejects_path_outside_presets(tmp_path: Path) -> None:
    repo_root, db_path, _ = _make_repo(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps({"name": "evil", "steps": [{"filter": "grayscale", "on": "image"}]}),
        encoding="utf-8",
    )
    add_preset("evil", str(outside.resolve()), db_path=db_path)

    with pytest.raises(PresetPathUnsafeError):
        resolve_preset_file("evil", db_path=db_path, repo_root=repo_root)


def test_resolve_preset_file_rejects_traversal_segments(tmp_path: Path) -> None:
    repo_root, db_path, presets_dir = _make_repo(tmp_path)
    secret = tmp_path / "secret.json"
    secret.write_text(
        json.dumps({"name": "secret", "steps": [{"filter": "grayscale", "on": "image"}]}),
        encoding="utf-8",
    )
    # Point through presets dir with .. into tmp_path
    relative = Path("backend") / "presets" / ".." / ".." / ".." / secret.name
    # Actually repo_root/backend/presets/../../../secret.json from repo = tmp_path/secret
    # stored as relative from repo_root:
    traversal = "backend/presets/../../../secret.json"
    # From repo_root: backend/presets/../../../secret.json -> tmp_path/secret.json
    add_preset("leaky", traversal, db_path=db_path)

    # Ensure the traversal target exists and would resolve if not sandboxed
    assert (repo_root / traversal).resolve() == secret.resolve()
    assert presets_dir.is_dir()

    with pytest.raises(PresetPathUnsafeError):
        resolve_preset_file("leaky", db_path=db_path, repo_root=repo_root)


def test_apply_named_preset_runs_grayscale_steps(tmp_path: Path) -> None:
    repo_root, db_path, presets_dir = _make_repo(tmp_path)
    _write_gray_preset(presets_dir)
    add_preset(
        "simple_gray",
        "backend/presets/simple_gray.json",
        db_path=db_path,
    )

    source = Image.new("RGB", (8, 8), color=(200, 40, 40))
    result = apply_named_preset(
        source,
        "simple_gray",
        db_path=db_path,
        repo_root=repo_root,
    )

    assert result.size == source.size
    assert result.mode in ("RGB", "RGBA", "L")
    pixel = result.convert("RGB").getpixel((0, 0))
    assert pixel[0] == pixel[1] == pixel[2]
    assert pixel != (200, 40, 40)


def test_preset_job_limiter_rejects_when_full() -> None:
    limiter = PresetJobLimiter(limit=1)

    async def _run() -> None:
        assert await limiter.try_acquire() is True
        assert await limiter.try_acquire() is False
        await limiter.release()
        assert await limiter.try_acquire() is True
        await limiter.release()

    asyncio.run(_run())


def test_run_preset_job_raises_busy_when_slot_taken(tmp_path: Path) -> None:
    repo_root, db_path, presets_dir = _make_repo(tmp_path)
    _write_gray_preset(presets_dir)
    add_preset(
        "simple_gray",
        "backend/presets/simple_gray.json",
        db_path=db_path,
    )
    limiter = PresetJobLimiter(limit=1)
    source = Image.new("RGB", (4, 4), color=(10, 20, 30))

    async def _run() -> None:
        assert await limiter.try_acquire() is True
        with pytest.raises(PresetBusyError):
            await run_preset_job(
                source,
                "simple_gray",
                limiter=limiter,
                db_path=db_path,
                repo_root=repo_root,
            )
        await limiter.release()
        result = await run_preset_job(
            source,
            "simple_gray",
            limiter=limiter,
            db_path=db_path,
            repo_root=repo_root,
        )
        assert result.size == source.size

    asyncio.run(_run())
