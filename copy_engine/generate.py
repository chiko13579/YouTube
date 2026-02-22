#!/usr/bin/env python3
"""
copy_engine/generate.py
マルチエージェントで「刺さるショート動画原稿」を生成するスクリプト

使い方:
    # テーマファイルからランダムに話のタネを選んで生成
    python generate.py --theme-file themes/01_自己肯定・自己承認.md --persona persona/persona.md

    # タネの番号を指定して生成
    python generate.py --theme-file themes/02_習慣・行動変容.md --seed 3 --persona persona/persona.md

    # 全テーマからランダムに選ぶ
    python generate.py --random --persona persona/persona.md

    # ラウンド数・モデルを指定
    python generate.py --theme-file themes/01_自己肯定・自己承認.md --rounds 3 --model gpt-4o

依存:
    pip install openai python-dotenv

環境変数（.envに記載）:
    OPENAI_API_KEY=sk-...
"""

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

THEMES_DIR = Path(__file__).parent / "themes"
PERSONA_DIR = Path(__file__).parent / "persona"
OUTPUT_DIR = Path(__file__).parent / "output"

# ─────────────────────────────────────────────
# 刺さる文章の「黄金法則」（全エージェントが共有）
# ─────────────────────────────────────────────
GOLDEN_RULES = """
【刺さる文章の7大要素】
① フック     ─ 今この瞬間の読者状態を正確に描写する
② 共感       ─ 読者の内言語をそのまま代弁する（「あんなこと言わなきゃよかった」等）
③ リフレーミング ─ 常識を覆す意外な真実を提示する（「夜の反省会は不幸になる練習」等）
④ 解決策     ─ 超シンプルで「自分にもできる」行動を示す（「騙されたと思って3つだけ」等）
⑤ 具体例     ─ 誰でも言える小さな例でリアリティを担保する
⑥ 約束       ─ 具体的な期間と変化のイメージを与える（「1ヶ月後〜」等）
⑦ 承認       ─ 読者の今日を肯定して温かく締める

【文体ルール】
- 総文字数：200〜350字（ショート動画の尺＝約1分）
- 一文は30字以内が理想
- 「……」で余白を作れ
- タイトルは30字以内
"""

# ─────────────────────────────────────────────
# ファイル読み込みユーティリティ
# ─────────────────────────────────────────────

def load_persona(path: Path) -> str:
    """persona.md を読み込んで文字列として返す"""
    if not path.exists():
        print(f"警告：人格ファイルが見つかりません: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def load_theme_seeds(path: Path) -> list[dict]:
    """
    テーマファイルを読み込んで話のタネリストを返す。
    フォーマット: 数字. タネ名\n   説明文
    """
    if not path.exists():
        print(f"エラー：テーマファイルが見つかりません: {path}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    seeds = []

    # 番号付きリスト行を検索（例：「1. タネ名」）
    pattern = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        num = int(match.group(1))
        title = match.group(2).strip()

        # タネ名の次の段落（説明文）を取得
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        description = text[start:end].strip()
        # 先頭の空行や記号を除去
        description = re.sub(r"^[\s\-─]+", "", description, flags=re.MULTILINE).strip()

        seeds.append({
            "number": num,
            "title": title,
            "description": description,
        })

    return seeds


def pick_seed(seeds: list[dict], seed_num: int | None = None) -> dict:
    """タネを選ぶ（番号指定 or ランダム）"""
    if seed_num is not None:
        for s in seeds:
            if s["number"] == seed_num:
                return s
        print(f"警告：タネ番号 {seed_num} が見つかりません。ランダムに選びます。")
    return random.choice(seeds)


def list_theme_files() -> list[Path]:
    """themes/ フォルダ内のすべての .md ファイルを返す"""
    return sorted(THEMES_DIR.glob("*.md"))


def pick_random_theme_and_seed() -> tuple[Path, dict]:
    """全テーマファイルからランダムにファイルとタネを選ぶ"""
    theme_files = list_theme_files()
    if not theme_files:
        print("エラー：themes/ フォルダにテーマファイルがありません。")
        sys.exit(1)
    theme_file = random.choice(theme_files)
    seeds = load_theme_seeds(theme_file)
    seed = random.choice(seeds)
    return theme_file, seed


# ─────────────────────────────────────────────
# エージェント定義
# ─────────────────────────────────────────────

def build_persona_section(persona: str) -> str:
    """人格定義をプロンプトに挿入できる形式に変換"""
    if not persona:
        return ""
    return f"""
【あなたが演じる人格】
以下の人格定義に完全に従って原稿を書いてください。
人格から外れた表現・価値観・口調は使用禁止です。

{persona}
"""


def agent_drafter(seed: dict, persona: str, model: str) -> dict:
    """ライター：話のタネから3パターンの初稿を作成する"""
    prompt = f"""
あなたはショート動画（TikTok/Instagram Reels/YouTube Shorts）の天才コピーライターです。

{build_persona_section(persona)}

以下の「話のタネ」を使って「人の心を掴む動画原稿」を3パターン書いてください。

【話のタネ】
タイトル：{seed['title']}
内容：{seed['description']}

{GOLDEN_RULES}

【3パターンの種類】
- パターンA（共感型）：痛みや自己嫌悪から入る。ターゲット：自分を責めやすい人
- パターンB（衝撃型）：常識を覆す意外な事実から入る。ターゲット：現状を変えたい人
- パターンC（ストーリー型）：第三者の実話・逸話から入る。ターゲット：感動・共感を求める人

各パターンにはタイトルと本文（セリフとして読み上げる原稿）を含めてください。

出力はJSON形式で：
{{
  "seed": "{seed['title']}",
  "patterns": [
    {{
      "type": "共感型",
      "title": "タイトル",
      "script": "本文（改行は\\nで）"
    }},
    {{
      "type": "衝撃型",
      "title": "タイトル",
      "script": "本文"
    }},
    {{
      "type": "ストーリー型",
      "title": "タイトル",
      "script": "本文"
    }}
  ]
}}
"""
    print("  [Drafter] 初稿3パターンを執筆中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    return json.loads(response.choices[0].message.content)


def agent_critic(draft: dict, persona: str, model: str) -> dict:
    """批評家：各パターンの弱点と改善案を指摘する"""
    prompt = f"""
あなたはショート動画コンテンツの厳格な編集長です。

{build_persona_section(persona)}

以下の原稿を「視聴者の目線」と「人格定義への一致度」の両面から批評してください。

【批評する原稿】
{json.dumps(draft, ensure_ascii=False, indent=2)}

各パターンについて：
1. 「離脱ポイント」（ここで見るのをやめると思う箇所とその理由）
2. 「7大要素の弱点」（どの要素が不足しているか）
3. 「人格ズレ」（人格定義と合っていない表現・口調）
4. 「具体的な改善案」

出力はJSON形式で：
{{
  "critiques": [
    {{
      "type": "共感型",
      "dropout_point": "〇〇の部分。理由：...",
      "weak_elements": ["要素名: 理由"],
      "persona_mismatch": "人格との不一致点（なければ「なし」）",
      "improvements": "具体的な改善案..."
    }},
    {{
      "type": "衝撃型",
      "dropout_point": "...",
      "weak_elements": [],
      "persona_mismatch": "...",
      "improvements": "..."
    }},
    {{
      "type": "ストーリー型",
      "dropout_point": "...",
      "weak_elements": [],
      "persona_mismatch": "...",
      "improvements": "..."
    }}
  ],
  "recommended_pattern": "最も可能性が高いパターン（共感型/衝撃型/ストーリー型）",
  "recommendation_reason": "理由..."
}}
"""
    print("  [Critic] 批評・弱点分析中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return json.loads(response.choices[0].message.content)


def agent_refiner(draft: dict, critique: dict, persona: str, model: str) -> dict:
    """磨き屋：批評を反映して改善稿を書く"""
    recommended = critique.get("recommended_pattern", "共感型")
    prompt = f"""
あなたはショート動画の天才コピーライターです。
批評家のフィードバックを完全に反映して、最も可能性が高いパターンを大幅改善してください。

{build_persona_section(persona)}

推奨パターン：{recommended}

【元の原稿】
{json.dumps(draft, ensure_ascii=False, indent=2)}

【批評家のフィードバック】
{json.dumps(critique, ensure_ascii=False, indent=2)}

改善稿を書いてください。
- 批評で指摘された全ての弱点を解消する
- 人格定義に完全に沿った口調・表現にする
- 「離脱ポイント」を完全になくす

出力はJSON形式で：
{{
  "type": "{recommended}",
  "title": "改善されたタイトル",
  "script": "改善された本文（改行は\\nで）",
  "changes_made": ["変更点1", "変更点2"]
}}
"""
    print("  [Refiner] 批評を反映して改善稿を執筆中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    return json.loads(response.choices[0].message.content)


def agent_devil(refined: dict, model: str) -> dict:
    """悪魔の代弁者：懐疑的な視聴者として最厳格チェック"""
    prompt = f"""
あなたは「絶対に感動しない」と決めている懐疑的な視聴者です。
以下の原稿を見て、正直な感想を述べてください。

【チェックする原稿】
タイトル：{refined.get('title', '')}
本文：{refined.get('script', '')}

1. 「うさんくさい」と感じる部分はどこか？
2. 「よくある話」と感じる部分はどこか？
3. 「で、結局何をしろというんだ」と感じる部分はどこか？
4. 最後まで見続けたいか？（理由も）
5. このタイトルで動画を開くか？（理由も）

出力はJSON形式で：
{{
  "suspicious_parts": "怪しいと感じる部分...",
  "cliche_parts": "よくある話だと感じる部分...",
  "unclear_action": "行動が不明瞭な部分...",
  "would_watch_to_end": true,
  "watch_reason": "理由...",
  "would_click_title": true,
  "click_reason": "理由...",
  "overall_score": 7,
  "one_advice": "一言アドバイス..."
}}
"""
    print("  [Devil's Advocate] 懐疑的な視聴者として最終チェック中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return json.loads(response.choices[0].message.content)


def agent_judge(refined: dict, devil: dict, model: str) -> dict:
    """審査員：7項目70点満点でスコアリング・合否判定"""
    prompt = f"""
あなたはショート動画マーケティングの専門家で、最終審査員です。

【審査する原稿】
タイトル：{refined.get('title', '')}
本文：{refined.get('script', '')}

【悪魔の代弁者の意見】
{json.dumps(devil, ensure_ascii=False, indent=2)}

以下の7項目を各10点満点で採点し、合計スコアを出してください：
1. フック力（最初の1文で続きを見たくなるか）
2. 共感度（読者の状態を正確に描写できているか）
3. リフレーミング力（意外な視点・真実を提示できているか）
4. 解決策のシンプルさ（誰でも今夜できるか）
5. 具体性（抽象的でなく映像が浮かぶか）
6. 変化の約束（希望を感じられるか）
7. 締めの余韻（見終わった後に温かい気持ちになるか）

55点以上 → 合格。54点以下 → 再修正。

出力はJSON形式で：
{{
  "scores": {{
    "hook": 8,
    "empathy": 7,
    "reframing": 8,
    "simplicity": 9,
    "concreteness": 7,
    "promise": 8,
    "closing": 8
  }},
  "total": 55,
  "verdict": "合格",
  "verdict_reason": "判定理由...",
  "final_advice": "最終アドバイス（採用稿への一言磨き指示）"
}}
"""
    print("  [Judge] 最終審査中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.5,
    )
    return json.loads(response.choices[0].message.content)


def agent_polisher(refined: dict, judge: dict, persona: str, model: str) -> dict:
    """仕上げ屋：審査員のアドバイスで最終磨きをかける"""
    prompt = f"""
あなたは言葉のプロフェッショナルです。

{build_persona_section(persona)}

審査員の最終アドバイスを反映して、この原稿を完璧に仕上げてください。

【採用原稿】
タイトル：{refined.get('title', '')}
本文：{refined.get('script', '')}

【審査員の最終アドバイス】
{judge.get('final_advice', '')}

内容は大きく変えず、言葉の選び方・句読点・改行・「……」のリズムを磨いてください。
人格定義の口調・口癖を最終確認して自然に反映させてください。

出力はJSON形式で：
{{
  "title": "最終タイトル",
  "script": "最終本文（改行は\\nで）",
  "word_count": 250
}}
"""
    print("  [Polisher] 最終磨き中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.6,
    )
    return json.loads(response.choices[0].message.content)


def agent_persona_checker(final: dict, persona: str, model: str) -> dict:
    """
    人格チェッカー：生成された原稿が人格定義と一致しているか審査する。
    5項目×10点 = 50点満点。40点以上で人格一致。
    """
    if not persona:
        return {"total": 50, "verdict": "スキップ（人格未定義）", "issues": [], "fixes": []}

    prompt = f"""
あなたは「人格の一貫性」を審査する専門家です。
以下の原稿が、定義された人格に忠実に書かれているかを厳密にチェックしてください。

【人格定義】
{persona}

【チェックする最終原稿】
タイトル：{final.get('title', '')}
本文：{final.get('script', '')}

以下の5項目を各10点満点で採点してください：

1. **口調一致度** (10点)
   - 定義された話し方・文体と一致しているか
   - 「……」「騙されたと思って」「今夜くらい」などの口癖が自然に使われているか

2. **価値観一致度** (10点)
   - 読者を責めていないか
   - 「許す・寄り添う」スタンスになっているか
   - 「変わらなければ」プレッシャーを与えていないか

3. **禁止表現チェック** (10点)
   - 禁止リストの言葉が使われていないか（使われていれば減点）

4. **口癖・特徴的表現の反映** (10点)
   - 人格固有の言い回しや表現が自然に入っているか

5. **ターゲット一致度** (10点)
   - 定義されたターゲット読者に向けた内容になっているか
   - 夜・疲れた時間帯の視聴シーンに合っているか

出力はJSON形式で：
{{
  "scores": {{
    "tone": 8,
    "values": 9,
    "forbidden_check": 10,
    "characteristic_phrases": 7,
    "target_alignment": 8
  }},
  "total": 42,
  "verdict": "人格一致",
  "issues": [
    "口調が少し固い。「〇〇してください」より「〇〇してみませんか」が人格に合う",
    "「絶対に」という表現は禁止リストにある"
  ],
  "fixes": [
    "「〇〇してください」→「〇〇してみませんか」に変更",
    "「絶対に」→「きっと」に変更"
  ]
}}

判定基準：
- 45〜50点：完璧な人格一致
- 38〜44点：人格一致（微調整で使用可）
- 30〜37点：要注意（再修正推奨）
- 29点以下：人格不一致（再生成推奨）
"""
    print("  [PersonaChecker] 人格一致度を審査中...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return json.loads(response.choices[0].message.content)


# ─────────────────────────────────────────────
# メインパイプライン
# ─────────────────────────────────────────────

def run_pipeline(
    seed: dict,
    persona: str,
    max_rounds: int = 2,
    model: str = "gpt-4o",
) -> dict:
    """マルチエージェントパイプラインを実行する"""

    print(f"\n{'='*60}")
    print(f"話のタネ：{seed['title']}")
    print(f"モデル：{model}  最大ラウンド数：{max_rounds}")
    print(f"{'='*60}\n")

    results = {
        "seed": seed,
        "model": model,
        "created_at": datetime.now().isoformat(),
        "rounds": [],
        "final": None,
        "persona_check": None,
    }

    refined = None
    judge = None

    for round_num in range(1, max_rounds + 1):
        print(f"\n--- ラウンド {round_num}/{max_rounds} ---")

        print("\n[Step 1] ライター（初稿作成）")
        if round_num == 1:
            draft = agent_drafter(seed, persona, model)
        else:
            # 2ラウンド目以降は前ラウンドの審査フィードバックをタネに追記
            modified_seed = dict(seed)
            modified_seed["description"] += f"\n\n前ラウンドの反省：{judge.get('verdict_reason', '')}"
            draft = agent_drafter(modified_seed, persona, model)

        print("\n[Step 2] 批評家（弱点・人格ズレ分析）")
        critique = agent_critic(draft, persona, model)

        print("\n[Step 3] 磨き屋（改善稿作成）")
        refined = agent_refiner(draft, critique, persona, model)

        print("\n[Step 4] 悪魔の代弁者（懐疑的チェック）")
        devil = agent_devil(refined, model)

        print("\n[Step 5] 審査員（コンテンツ採点）")
        judge = agent_judge(refined, devil, model)

        round_result = {
            "round": round_num,
            "draft": draft,
            "critique": critique,
            "refined": refined,
            "devil": devil,
            "judge": judge,
        }
        results["rounds"].append(round_result)

        score = judge.get("total", 0)
        verdict = judge.get("verdict", "再修正")
        print(f"\n  ★ コンテンツスコア：{score}/70点  判定：{verdict}")

        if verdict == "合格":
            print("  ✓ 合格！最終磨きに進みます。")
            break
        else:
            if round_num < max_rounds:
                print(f"  → 再修正。ラウンド {round_num + 1} に進みます。")
            else:
                print("  → 最大ラウンド到達。最良稿で最終磨きに進みます。")

    print(f"\n[Step 6] 仕上げ屋（最終磨き）")
    final = agent_polisher(refined, judge, persona, model)
    results["final"] = final

    print(f"\n[Step 7] 人格チェッカー（人格一致度審査）")
    persona_check = agent_persona_checker(final, persona, model)
    results["persona_check"] = persona_check

    persona_score = persona_check.get("total", "-")
    persona_verdict = persona_check.get("verdict", "-")
    print(f"  ★ 人格スコア：{persona_score}/50点  判定：{persona_verdict}")

    if persona_check.get("issues"):
        print("  ⚠ 人格の問題点：")
        for issue in persona_check["issues"]:
            print(f"    - {issue}")

    return results


# ─────────────────────────────────────────────
# 出力・保存
# ─────────────────────────────────────────────

def print_final(results: dict):
    """最終結果をターミナルに表示する"""
    final = results.get("final", {})
    judge = results["rounds"][-1]["judge"]
    scores = judge.get("scores", {})
    persona_check = results.get("persona_check", {})
    p_scores = persona_check.get("scores", {})

    print(f"\n{'='*60}")
    print("【最終原稿】")
    print(f"{'='*60}")
    print(f"\nタイトル：{final.get('title', '')}\n")
    print(final.get("script", "").replace("\\n", "\n"))
    print(f"\n文字数：{final.get('word_count', '-')}字")

    print(f"\n{'─'*40}")
    print(f"【コンテンツ採点】合計：{judge.get('total', '-')}/70点  判定：{judge.get('verdict', '-')}")
    content_labels = {
        "hook": "フック力", "empathy": "共感度", "reframing": "リフレーミング",
        "simplicity": "シンプルさ", "concreteness": "具体性",
        "promise": "変化の約束", "closing": "締めの余韻",
    }
    for key, label in content_labels.items():
        val = scores.get(key, 0)
        bar = "█" * val + "░" * (10 - val)
        print(f"  {label:14s} [{bar}] {val}/10")

    print(f"\n{'─'*40}")
    print(f"【人格チェック】合計：{persona_check.get('total', '-')}/50点  判定：{persona_check.get('verdict', '-')}")
    persona_labels = {
        "tone": "口調一致度", "values": "価値観一致度", "forbidden_check": "禁止表現チェック",
        "characteristic_phrases": "口癖の反映", "target_alignment": "ターゲット一致",
    }
    for key, label in persona_labels.items():
        val = p_scores.get(key, 0)
        bar = "█" * val + "░" * (10 - val)
        print(f"  {label:18s} [{bar}] {val}/10")

    fixes = persona_check.get("fixes", [])
    if fixes:
        print(f"\n  修正提案：")
        for f in fixes:
            print(f"    → {f}")


def save_results(results: dict) -> Path:
    """結果をファイルに保存する"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    seed_title = results["seed"]["title"][:20].replace(" ", "_").replace("/", "-")
    filepath = OUTPUT_DIR / f"{timestamp}_{seed_title}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 読みやすいテキスト版
    txt_path = filepath.with_suffix(".txt")
    final = results.get("final", {})
    judge_data = results["rounds"][-1]["judge"]
    persona_check = results.get("persona_check", {})

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"話のタネ：{results['seed']['title']}\n")
        f.write(f"作成日時：{results['created_at']}\n")
        f.write(f"ラウンド数：{len(results['rounds'])}\n")
        f.write(f"コンテンツスコア：{judge_data.get('total', '-')}/70点\n")
        f.write(f"人格スコア：{persona_check.get('total', '-')}/50点  {persona_check.get('verdict', '-')}\n\n")
        f.write("=" * 50 + "\n")
        f.write(f"【タイトル】\n{final.get('title', '')}\n\n")
        f.write(f"【本文】\n{final.get('script', '').replace(chr(92) + 'n', chr(10))}\n\n")
        if persona_check.get("issues"):
            f.write("=" * 50 + "\n")
            f.write("【人格の問題点と修正提案】\n")
            for issue, fix in zip(persona_check.get("issues", []), persona_check.get("fixes", [])):
                f.write(f"  問題：{issue}\n")
                f.write(f"  修正：{fix}\n\n")

    return txt_path


# ─────────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="マルチエージェントで刺さるショート動画原稿を生成する"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--theme-file", "-f", type=Path, help="使用するテーマファイルのパス（themes/フォルダ内）")
    group.add_argument("--random", "-r", action="store_true", help="全テーマからランダムにタネを選ぶ")

    parser.add_argument("--seed", "-s", type=int, default=None, help="タネの番号（省略するとランダム）")
    parser.add_argument("--persona", "-p", type=Path, default=PERSONA_DIR / "persona.md", help="人格定義ファイルのパス")
    parser.add_argument("--rounds", type=int, default=2, help="最大ラウンド数（デフォルト：2）")
    parser.add_argument("--model", "-m", default="gpt-4o", help="使用するモデル（デフォルト：gpt-4o）")
    parser.add_argument("--list", "-l", action="store_true", help="テーマファイル内のタネ一覧を表示して終了")

    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("エラー：OPENAI_API_KEY が設定されていません。.env ファイルを確認してください。")
        sys.exit(1)

    # タネ一覧表示モード
    if args.list:
        if not args.theme_file:
            print("--list には --theme-file も指定してください。")
            sys.exit(1)
        seeds = load_theme_seeds(args.theme_file)
        print(f"\n【{args.theme_file.stem}】の話のタネ一覧\n")
        for s in seeds:
            print(f"  {s['number']:2d}. {s['title']}")
        print()
        sys.exit(0)

    # 話のタネを選ぶ
    if args.random:
        theme_file, seed = pick_random_theme_and_seed()
        print(f"\nランダム選択：{theme_file.name} → タネ {seed['number']}「{seed['title']}」")
    else:
        theme_file = args.theme_file
        seeds = load_theme_seeds(theme_file)
        seed = pick_seed(seeds, args.seed)
        print(f"\nテーマ：{theme_file.name} → タネ {seed['number']}「{seed['title']}」")

    # 人格を読み込む
    persona = load_persona(args.persona)

    # パイプライン実行
    results = run_pipeline(
        seed=seed,
        persona=persona,
        max_rounds=args.rounds,
        model=args.model,
    )

    # 結果表示と保存
    print_final(results)
    saved_path = save_results(results)
    print(f"\n\n保存先：{saved_path}")
    print(f"詳細JSON：{saved_path.with_suffix('.json')}")


if __name__ == "__main__":
    main()
