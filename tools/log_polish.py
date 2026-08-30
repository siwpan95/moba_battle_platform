#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对战日志润色模块 —— 调用 DeepSeek 在线模型把对战日志改写成武侠短篇。

风格从港漫名家名单中随机抽取（见 hk_comic_styles.py）。

单独使用：
    python tools/log_polish.py logs/battle_20260809_074512.log
    python tools/log_polish.py logs/xxx.log --match 1 --master 马荣成
    python tools/log_polish.py logs/xxx.log --all --seed 42

也可被 run_battle_sim.py 通过 --polish 调用。

API Key 优先级：--api-key > 环境变量 DEEPSEEK_API_KEY > 内置默认值
"""

import argparse
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    requests = None

from tools.hk_comic_styles import (      # noqa: E402
    HK_COMIC_MASTERS, build_style_prompt, get_master, list_master_names,
)

DEFAULT_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 2026-08-27 安全修复：原明文密钥已公开泄露，密钥仅经环境变量注入
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"

# 单场分隔行形如：【第 1/3 场】哈格尼斯[...] VS 若陀龙王[...]   先手: P2
MATCH_HEADER_RE = re.compile(r"^【第\s*(\d+)\s*/\s*(\d+)\s*场】(.*)$")


class PolishError(Exception):
    pass


# 私人令牌.txt 位于项目根目录，形如：
#   第一行：gitee
#   第二行：<gitee 令牌>   （与本功能无关）
#   第三行：<模型名>       （如 deepseek-v4-pro）
#   第四行：<DeepSeek API Key>
_TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "私人令牌.txt"
)


def load_token_file(path=None):
    """读取私人令牌.txt，返回 (api_key, model)。

    第 3 行为模型名，第 4 行为 DeepSeek API Key；缺失则返回 (None, None)。
    解析失败时尽可能返回已读取到的部分（例如只有 Key 没有 model）。
    """
    path = path or _TOKEN_FILE
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines()]
    except OSError:
        return None, None
    lines = [ln for ln in lines if ln]  # 跳过空行，便于按"第N个非空项"定位
    api_key = None
    model = None
    # 倒序找首个 sk- 开头的作为 Key（避免误取 gitee 令牌）
    for ln in reversed(lines):
        if ln.startswith("sk-"):
            api_key = ln
            break
    # 模型名：取最后一个非 sk- 的非空项（位于 Key 之前）
    for ln in reversed(lines):
        if ln != api_key and not ln.startswith("sk-"):
            model = ln
            break
    return api_key, model


def save_token_file(api_key, model, path=None):
    """写入/更新 私人令牌.txt 的模型与 API Key 行。

    规则（保平安）：保留文件中所有与旧 model / 旧 key 无关的行（如 gitee 令牌），
    仅在文件中存在旧 key（sk- 开头）时，才移除旧 key 行与其前的旧 model 行；
    最后追加新的 model 行与 key 行，保证 load_token_file 可正确解析。
    文件始终位于本地且已被 .gitignore 忽略，绝不入库。
    """
    path = path or _TOKEN_FILE
    old_key, old_model = load_token_file(path)
    lines = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.rstrip("\r\n") for ln in f.read().splitlines()]
        except OSError:
            lines = []
    kept = []
    for ln in lines:
        s = ln.strip()
        if s and s != old_key:
            kept.append(ln)
    if old_key:
        # 旧 key 存在时，其前最后一个非空行即旧 model 行，可安全移除
        while kept and not kept[-1].strip():
            kept.pop()
        if kept and kept[-1].strip() == old_model:
            kept.pop()
    while kept and not kept[-1].strip():
        kept.pop()
    kept.append(str(model).strip())
    kept.append(str(api_key).strip())
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except OSError:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")


def resolve_api_key(cli_key=None, file_key=None):
    """API Key 解析优先级：cli > 环境变量 > 令牌文件 > 内置默认值。"""
    return cli_key or os.environ.get("DEEPSEEK_API_KEY") or file_key or DEFAULT_API_KEY


def resolve_model(cli_model=None, file_model=None):
    """模型名解析优先级：cli > 令牌文件 > 内置默认值。"""
    return cli_model or file_model or DEFAULT_MODEL


def resolve_credentials(cli_key=None, cli_model=None, token_path=None):
    """一次性解析 (api_key, model)，自动合并私人令牌.txt。"""
    fkey, fmodel = load_token_file(token_path)
    return resolve_api_key(cli_key, fkey), resolve_model(cli_model, fmodel)


def split_matches(log_text):
    """把整份日志按场次切开，返回 [{'index':1,'header':..,'body':..}, ...]"""
    lines = log_text.splitlines()
    matches, cur = [], None
    for ln in lines:
        stripped = ln.strip()
        m = MATCH_HEADER_RE.match(stripped)
        if m:
            if cur:
                matches.append(cur)
            cur = {"index": int(m.group(1)), "header": m.group(3).strip(), "body": []}
        elif cur is not None:
            if set(stripped) <= {"─", "="} and stripped:
                continue          # 跳过纯分隔线
            if stripped.startswith("统计汇总"):
                break
            if stripped:
                cur["body"].append(stripped)
    if cur:
        matches.append(cur)
    for mt in matches:
        mt["body"] = "\n".join(mt["body"])
    return matches


def build_messages(match, master, max_chars=6000):
    """构造发给模型的对话。"""
    body = match["body"]
    truncated = False
    if len(body) > max_chars:
        body = body[:max_chars]
        truncated = True

    style = build_style_prompt(master)
    sys_prompt = (
        "你是一位精通香港漫画叙事的武侠小说写手。"
        "用户会给你一份游戏对战的结构化战斗日志，"
        "你要把它改写成一篇有头有尾的中文武侠短篇。\n\n"
        "硬性要求：\n"
        "1. 必须忠于日志中的事实：出场人物、出招顺序、谁被控制、"
        "谁暴击、护盾吸收、最终谁胜谁负，都不可篡改；\n"
        "2. 伤害数字不要直接罗列，要转化为文学化的力度描写；\n"
        "3. 保留招式的中文描述意象，可为其起一个港漫式的招式名；\n"
        "4. 篇幅 600–1200 字，分段清晰，不要用 Markdown 标题；\n"
        "5. 只输出小说正文，不要任何解释、前言或后记。\n"
    )
    user_prompt = (
        f"{style}\n"
        f"=== 对战梗概 ===\n{match['header']}\n\n"
        f"=== 战斗日志 ===\n{body}\n"
        + ("\n（日志过长已截断，请据已有内容合理收束结局）\n" if truncated else "")
        + "\n请开始创作这篇武侠短篇。"
    )
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_deepseek(messages, api_key, model=DEFAULT_MODEL,
                  base_url=DEFAULT_BASE_URL, temperature=1.0,
                  timeout=180, retries=3):
    """调用 DeepSeek chat/completions，返回正文字符串。"""
    if requests is None:
        raise PolishError("缺少 requests 库，请先 pip install requests")

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers,
                                 data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip(), data.get("usage", {})
            # 401/402 这类错误重试无意义，直接抛
            if resp.status_code in (401, 402, 403):
                raise PolishError(
                    f"HTTP {resp.status_code}：{resp.text[:300]}"
                    "（请检查 API Key 是否有效、账户是否有余额）")
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except PolishError:
            raise
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(2 * attempt)
    raise PolishError(f"调用失败（重试 {retries} 次）：{last_err}")


def polish_match(match, api_key, master=None, rng=None, **kw):
    """润色单场对战，返回 dict。"""
    rng = rng or random
    master = master or rng.choice(HK_COMIC_MASTERS)
    messages = build_messages(match, master)
    text, usage = call_deepseek(messages, api_key, **kw)
    return {
        "match_index": match["index"],
        "header": match["header"],
        "master": master["name"],
        "works": master["works"],
        "story": text,
        "usage": usage,
    }


def polish_log_file(log_path, api_key, indices=None, master_name=None,
                    seed=None, outdir=None, model=None,
                    base_url=DEFAULT_BASE_URL, temperature=1.0, verbose=True):
    """润色整份日志中的指定场次，产出 <原名>_wuxia.md 与 .json。

    api_key / model 若未显式传入，会自动从私人令牌.txt 与内置默认值合并。
    """
    api_key = resolve_api_key(api_key)
    model = resolve_model(model)
    with open(log_path, "r", encoding="utf-8") as f:
        log_text = f.read()

    matches = split_matches(log_text)
    if not matches:
        raise PolishError(f"未能从 {log_path} 解析出任何场次")

    if indices:
        want = set(indices)
        matches = [m for m in matches if m["index"] in want]
        if not matches:
            raise PolishError(f"指定场次 {sorted(want)} 不存在")

    rng = random.Random(seed)
    fixed_master = get_master(master_name) if master_name else None
    if master_name and not fixed_master:
        raise PolishError(
            f"未知港漫名家：{master_name}，可选：{'、'.join(list_master_names())}")

    outdir = outdir or os.path.dirname(os.path.abspath(log_path))
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(log_path))[0]
    md_path = os.path.join(outdir, f"{base}_wuxia.md")
    js_path = os.path.join(outdir, f"{base}_wuxia.json")

    results, failures = [], []
    for i, mt in enumerate(matches, 1):
        master = fixed_master or rng.choice(HK_COMIC_MASTERS)
        if verbose:
            print(f"[{i}/{len(matches)}] 润色第 {mt['index']} 场 "
                  f"（风格：{master['name']}）…", flush=True)
        try:
            res = polish_match(mt, api_key, master=master, rng=rng,
                               model=model, base_url=base_url,
                               temperature=temperature)
            results.append(res)
            if verbose:
                print(f"    完成，{len(res['story'])} 字")
        except PolishError as e:
            failures.append({"match_index": mt["index"], "error": str(e)})
            if verbose:
                print(f"    失败：{e}", file=sys.stderr)
            # Key/余额问题会持续失败，早停避免无谓重试
            if "401" in str(e) or "402" in str(e) or "403" in str(e):
                if verbose:
                    print("    检测到鉴权/余额问题，停止后续润色。", file=sys.stderr)
                break

    if results:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# 对战武侠短篇集\n\n")
            f.write(f"> 源日志：`{os.path.basename(log_path)}`　"
                    f"模型：{model}　共 {len(results)} 篇\n\n")
            for r in results:
                f.write(f"---\n\n## 第 {r['match_index']} 场・{r['master']}风\n\n")
                f.write(f"> 对阵：{r['header']}\n>\n")
                f.write(f"> 风格取法：{r['master']}（{r['works']}）\n\n")
                f.write(r["story"] + "\n\n")
        with open(js_path, "w", encoding="utf-8") as f:
            json.dump({"source_log": os.path.basename(log_path),
                       "model": model,
                       "count": len(results),
                       "failures": failures,
                       "stories": results}, f, ensure_ascii=False, indent=2)

    return {"md": md_path if results else None,
            "json": js_path if results else None,
            "ok": len(results), "failed": len(failures),
            "failures": failures}


def main(argv=None):
    ap = argparse.ArgumentParser(description="把对战日志润色为港漫风武侠短篇")
    ap.add_argument("logfile", nargs="?", help="对战日志 .log 路径")
    ap.add_argument("--match", type=int, nargs="*", default=None,
                    help="指定场次号（可多个）；默认只润色第 1 场")
    ap.add_argument("--all", action="store_true", help="润色全部场次")
    ap.add_argument("--master", default=None,
                    help=f"固定风格，可选：{'、'.join(list_master_names())}")
    ap.add_argument("--seed", type=int, default=None, help="风格随机种子")
    ap.add_argument("--api-key", default=None, help="DeepSeek API Key（缺省读私人令牌.txt）")
    ap.add_argument("--model", default=None, help="模型名（缺省读私人令牌.txt，再回落内置默认）")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--list-masters", action="store_true", help="列出名家名单后退出")
    a = ap.parse_args(argv)

    if a.list_masters:
        for m in HK_COMIC_MASTERS:
            print(f"  {m['name']}（{m['works']}）")
        return 0

    if not a.logfile:
        ap.error("需要提供日志文件路径（或使用 --list-masters）")
    if not os.path.isfile(a.logfile):
        print(f"[错误] 日志不存在：{a.logfile}", file=sys.stderr)
        return 2

    indices = None if a.all else (a.match or [1])

    try:
        api_key, model = resolve_credentials(a.api_key, a.model)
        r = polish_log_file(
            a.logfile, api_key, indices=indices,
            master_name=a.master, seed=a.seed, outdir=a.outdir,
            model=model, base_url=a.base_url, temperature=a.temperature)
    except PolishError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    print(f"\n成功 {r['ok']} 篇，失败 {r['failed']} 篇")
    if r["md"]:
        print(f"武侠短篇: {r['md']}")
        print(f"结构化  : {r['json']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
