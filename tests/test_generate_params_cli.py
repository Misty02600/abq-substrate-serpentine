from pathlib import Path

import pytest

import generate_params as gp


def test_has_hydra_config_override_detects_split_and_inline_forms():
    assert gp._has_hydra_config_override(["--config-path", "conf"])
    assert gp._has_hydra_config_override(["--config-name=config"])
    assert not gp._has_hydra_config_override(["--multirun"])


def test_inject_selected_config_appends_hydra_args():
    args = ["--multirun"]
    updated = gp._inject_selected_config(args, r"D:\proj\conf\custom.yaml")

    assert updated[:1] == ["--multirun"]
    assert "--config-path" in updated
    assert "--config-name" in updated
    assert updated[-1] == "custom"


def test_prepare_cli_args_returns_original_when_override_present():
    """当用户手动指定 --config-path 时，直接返回原始参数，不弹窗。"""
    argv = ["generate_params.py", "--multirun", "--config-path", "conf"]
    assert gp._prepare_cli_args(argv) == argv


def test_prepare_cli_args_injects_selected_file(monkeypatch, tmp_path: Path):
    """无 --config-path 时弹窗选择文件，并注入 Hydra 参数。"""
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    selected_file = conf_dir / "picked.yaml"
    selected_file.write_text("wire:\n  w: 0.5\n", encoding="utf-8")

    monkeypatch.setattr(gp, "select_files", lambda **_: str(selected_file))

    argv = ["generate_params.py", "--multirun"]
    updated = gp._prepare_cli_args(argv)

    assert updated[0] == "generate_params.py"
    assert updated[1] == "--multirun"
    assert "--config-path" in updated
    assert "--config-name" in updated
    assert updated[-1] == "picked"


def test_prepare_cli_args_cancel_selection_raises_system_exit(monkeypatch):
    """用户取消文件选择时应抛出 SystemExit。"""
    monkeypatch.setattr(gp, "select_files", lambda **_: None)
    argv = ["generate_params.py", "--multirun"]

    with pytest.raises(SystemExit):
        gp._prepare_cli_args(argv)
