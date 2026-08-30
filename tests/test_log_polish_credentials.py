#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools.log_polish 凭据读写单元测试。

覆盖：私人令牌.txt 的保存/读取往返、gitee 令牌行保留、旧 key/model 更新、
文件缺失时的首次创建。
"""

from tools.log_polish import load_token_file, save_token_file


def test_save_creates_file_and_roundtrip(tmp_path):
    path = tmp_path / "私人令牌.txt"
    save_token_file("sk-test-abc123", "deepseek-v4-pro", path=path)
    key, model = load_token_file(path=path)
    assert key == "sk-test-abc123"
    assert model == "deepseek-v4-pro"


def test_save_preserves_unrelated_lines(tmp_path):
    path = tmp_path / "私人令牌.txt"
    path.write_text("gitee\nsome-gitee-token-xyz\n", encoding="utf-8")
    save_token_file("sk-new-key", "deepseek-v4-pro", path=path)
    text = path.read_text(encoding="utf-8")
    assert "gitee" in text
    assert "some-gitee-token-xyz" in text
    key, model = load_token_file(path=path)
    assert key == "sk-new-key"
    assert model == "deepseek-v4-pro"


def test_save_updates_existing_key_and_model(tmp_path):
    path = tmp_path / "私人令牌.txt"
    path.write_text(
        "gitee\nsome-gitee-token-xyz\ndeepseek-v4-pro\nsk-old-key\n",
        encoding="utf-8",
    )
    save_token_file("sk-new-key", "deepseek-chat", path=path)
    text = path.read_text(encoding="utf-8")
    # 旧 key / 旧 model 不残留，gitee 行保留，新值各出现一次
    assert "sk-old-key" not in text
    assert "some-gitee-token-xyz" in text
    assert text.count("sk-new-key") == 1
    assert text.rstrip().endswith("sk-new-key")
    key, model = load_token_file(path=path)
    assert key == "sk-new-key"
    assert model == "deepseek-chat"


def test_save_without_old_key_does_not_drop_other_lines(tmp_path):
    path = tmp_path / "私人令牌.txt"
    # 无旧 key 时，最后一行非 sk- 内容会被 loader 视作 model，
    # 保存不得把它当旧 model 删掉（保平安规则）
    path.write_text("gitee\nsome-gitee-token-xyz\n", encoding="utf-8")
    save_token_file("sk-first-key", "deepseek-v4-pro", path=path)
    text = path.read_text(encoding="utf-8")
    assert "gitee" in text and "some-gitee-token-xyz" in text
    key, model = load_token_file(path=path)
    assert key == "sk-first-key"
    assert model == "deepseek-v4-pro"
