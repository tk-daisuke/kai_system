# -*- coding: utf-8 -*-
"""ConfigManager 単体テスト"""
import tempfile
from pathlib import Path

import pytest
import yaml

from core.config_manager import ConfigManager, ActionConfig, GroupConfig, WorkflowConfig


@pytest.fixture
def tmp_config():
    """一時ディレクトリで初期化されたConfigManager"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 最小限の設定ファイルを作成
        actions_data = {"actions": [
            {"id": "a1", "name": "Action1", "type": "shell_cmd", "group": "G1",
             "display_order": 1, "params": {"command": "echo hello"}},
            {"id": "a2", "name": "Action2", "type": "scraper", "group": "G1",
             "display_order": 2, "enabled": False, "params": {}},
        ]}
        groups_data = {"groups": [
            {"name": "G1", "display_order": 1, "color": "#FF0000", "icon": "T"},
        ]}
        with open(td / "actions.yaml", "w") as f:
            yaml.dump(actions_data, f, allow_unicode=True)
        with open(td / "groups.yaml", "w") as f:
            yaml.dump(groups_data, f, allow_unicode=True)

        cm = ConfigManager(config_dir=td)
        cm.load()
        yield cm


class TestLoadAndQuery:

    def test_load_actions(self, tmp_config):
        assert len(tmp_config._actions) == 2
        assert tmp_config._actions[0].id == "a1"

    def test_get_all_actions_excludes_disabled(self, tmp_config):
        enabled = tmp_config.get_all_actions()
        assert len(enabled) == 1
        assert enabled[0].id == "a1"

    def test_get_action_by_id(self, tmp_config):
        a = tmp_config.get_action_by_id("a1")
        assert a is not None
        assert a.name == "Action1"

    def test_get_action_by_id_not_found(self, tmp_config):
        assert tmp_config.get_action_by_id("nonexistent") is None

    def test_get_groups(self, tmp_config):
        groups = tmp_config.get_groups()
        assert len(groups) == 1
        assert groups[0].name == "G1"

    def test_get_actions_by_group(self, tmp_config):
        actions = tmp_config.get_actions_by_group("G1")
        assert len(actions) == 1  # a2 is disabled

    def test_get_ungrouped_actions(self, tmp_config):
        ungrouped = tmp_config.get_ungrouped_actions()
        assert len(ungrouped) == 0


class TestActionCRUD:

    def test_add_action(self, tmp_config):
        data = {"id": "a3", "name": "New", "type": "shell_cmd", "params": {}}
        a = tmp_config.add_action(data)
        assert a.id == "a3"
        assert any(x.id == "a3" for x in tmp_config._actions)

    def test_add_duplicate_action_raises(self, tmp_config):
        data = {"id": "a1", "name": "Dup", "type": "shell_cmd", "params": {}}
        with pytest.raises(ValueError, match="重複"):
            tmp_config.add_action(data)

    def test_update_action(self, tmp_config):
        updated = tmp_config.update_action("a1", {
            "id": "a1", "name": "Updated", "type": "shell_cmd", "params": {}
        })
        assert updated.name == "Updated"

    def test_update_nonexistent_raises(self, tmp_config):
        with pytest.raises(KeyError):
            tmp_config.update_action("xxx", {"id": "xxx", "name": "X", "type": "shell_cmd"})

    def test_delete_action(self, tmp_config):
        tmp_config.delete_action("a1")
        assert all(x.id != "a1" for x in tmp_config._actions)

    def test_delete_nonexistent_raises(self, tmp_config):
        with pytest.raises(KeyError):
            tmp_config.delete_action("nonexistent")

    def test_duplicate_action(self, tmp_config):
        dup = tmp_config.duplicate_action("a1")
        assert dup.id == "a1_copy"
        assert "コピー" in dup.name

    def test_duplicate_nonexistent_raises(self, tmp_config):
        with pytest.raises(KeyError):
            tmp_config.duplicate_action("nonexistent")


class TestGroupCRUD:

    def test_add_group(self, tmp_config):
        g = tmp_config.add_group({"name": "G2", "display_order": 2})
        assert g.name == "G2"

    def test_add_duplicate_group_raises(self, tmp_config):
        with pytest.raises(ValueError, match="重複"):
            tmp_config.add_group({"name": "G1"})

    def test_update_group(self, tmp_config):
        g = tmp_config.update_group("G1", {"name": "G1_new", "display_order": 1})
        assert g.name == "G1_new"
        # 所属アクションも更新
        assert tmp_config._actions[0].group == "G1_new"

    def test_delete_group_clears_membership(self, tmp_config):
        tmp_config.delete_group("G1")
        assert len(tmp_config._groups) == 0
        assert tmp_config._actions[0].group == ""


class TestWorkflowCRUD:

    def test_add_workflow(self, tmp_config):
        w = tmp_config.add_workflow({"id": "wf1", "name": "WF", "action_ids": ["a1"]})
        assert w.id == "wf1"

    def test_add_duplicate_workflow_raises(self, tmp_config):
        tmp_config.add_workflow({"id": "wf1", "name": "WF"})
        with pytest.raises(ValueError, match="重複"):
            tmp_config.add_workflow({"id": "wf1", "name": "WF2"})

    def test_update_workflow(self, tmp_config):
        tmp_config.add_workflow({"id": "wf1", "name": "WF"})
        w = tmp_config.update_workflow("wf1", {"name": "Updated"})
        assert w.name == "Updated"
        assert w.id == "wf1"

    def test_delete_workflow(self, tmp_config):
        tmp_config.add_workflow({"id": "wf1", "name": "WF"})
        tmp_config.delete_workflow("wf1")
        assert len(tmp_config._workflows) == 0


class TestSavePersistence:

    def test_save_and_reload(self, tmp_config):
        tmp_config.add_action({"id": "a_new", "name": "Persist", "type": "shell_cmd", "params": {}})
        tmp_config.save_actions()
        # 新しいインスタンスで再読み込み
        cm2 = ConfigManager(config_dir=tmp_config.config_dir)
        cm2.load()
        assert any(x.id == "a_new" for x in cm2._actions)


class TestBackup:

    def test_backup_and_list(self, tmp_config):
        ts = tmp_config.backup_config()
        assert ts  # タイムスタンプ文字列
        backups = tmp_config.list_backups()
        assert len(backups) >= 1

    def test_restore_invalid_timestamp(self, tmp_config):
        with pytest.raises(ValueError, match="無効"):
            tmp_config.restore_config("../evil")


class TestDataClasses:

    def test_action_to_dict_roundtrip(self):
        data = {"id": "x", "name": "X", "type": "shell_cmd", "params": {"command": "ls"}}
        a = ActionConfig(data)
        d = a.to_dict()
        assert d["id"] == "x"
        assert d["params"]["command"] == "ls"

    def test_group_to_dict(self):
        g = GroupConfig({"name": "test", "display_order": 1})
        assert g.to_dict()["name"] == "test"

    def test_workflow_to_dict(self):
        w = WorkflowConfig({"id": "w1", "name": "W", "action_ids": ["a1"]})
        d = w.to_dict()
        assert d["id"] == "w1"
        assert d["action_ids"] == ["a1"]
