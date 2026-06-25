"""深度分析聊天记录 —— 提取更丰富的个人风格特征。"""
import json
import re
import time
import yaml
from pathlib import Path
from collections import Counter, defaultdict

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _get_data_dir():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return Path(cfg.get("data", {}).get("records_dir", "./data/chat_records"))
    return Path("./data/chat_records")


DATA_DIR = _get_data_dir()
DATA = DATA_DIR / "my_messages_cleaned.json"
OUTPUT = DATA_DIR / "deep_profile.txt"


def load():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze(msgs):
    total = len(msgs)
    results = {}

    # === 1. 消息长度分布 ===
    lengths = [len(m) for m in msgs]
    results["avg_len"] = round(sum(lengths) / total, 1)
    results["short_ratio"] = round(sum(1 for l in lengths if l <= 5) / total, 2)  # 短回复比例
    results["long_ratio"] = round(sum(1 for l in lengths if l >= 20) / total, 2)  # 长回复比例

    # === 2. 表情符号 ===
    emoji_pat = re.compile(r'\[[一-鿿㐀-䶿a-zA-Z]{1,6}\]')
    emoji_counter = Counter()
    emoji_count = 0
    for m in msgs:
        found = emoji_pat.findall(m)
        for e in found:
            emoji_counter[e] += 1
            emoji_count += 1
    results["top_emojis"] = emoji_counter.most_common(15)
    results["emoji_usage_rate"] = round(emoji_count / total, 2)

    # === 3. 高频词（结巴分词） ===
    import jieba
    all_words = []
    for m in msgs:
        words = jieba.lcut(m)
        all_words.extend([w for w in words if len(w) > 1])

    stop = {"哈哈","嗯嗯","哦哦","啊啊","呃呃","呜呜","喂喂","这个","那个","什么","怎么",
            "为什么","可以","没有","就是","然后","但是","因为","所以","如果","的话",
            "一个","一下","一点","一直","已经","不是","还是","觉得","知道","应该",
            "可能","真的","其实","这样","你们","我们","他们","她们","东西","这些",
            "那些","还是","不过","而且","或者","还有","比较","非常","特别","虽然"}
    filtered = [w for w in all_words if w not in stop]
    results["top_words"] = Counter(filtered).most_common(30)

    # === 4. 句尾模式 ===
    endings = Counter()
    for m in msgs:
        last = m[-1]
        if last in "哈呢呀吧哦嘛啊啦滴咯的了么呢吧呀":
            endings[last] += 1
        elif last in "~～！!？?….":
            endings[last] += 1
    results["top_endings"] = endings.most_common(10)

    # === 5. 常见开头 ===
    openings = Counter()
    for m in msgs:
        if len(m) >= 2:
            first2 = m[:2]
            if any(c in first2 for c in "我你那他她这在那是就好可不过还也"):
                openings[first2] += 1
        first1 = m[0]
        if first1 in "我好那可这也不过":
            openings[first1] += 1
    results["top_openings"] = openings.most_common(10)

    # === 6. 消息类型分类 ===
    types = {
        "简短确认": 0,   # 好/OK/行/嗯/对/是的/可以
        "疑问反问": 0,   # 包含？
        "解释说明": 0,   # 超过15字
        "情绪表达": 0,   # 包含哈哈/笑/哭/啧/唉
        "行动安排": 0,   # 包含来/去/到/给/发/送/拿
    }
    for m in msgs:
        if len(m) <= 4 and any(w in m for w in ["好","OK","行","嗯","对","是的","可以","ok","OK","👌"]):
            types["简短确认"] += 1
        elif "?" in m or "？" in m:
            types["疑问反问"] += 1
        elif len(m) > 15:
            types["解释说明"] += 1
        if any(w in m for w in ["哈哈","笑","哭","啧","唉","天","烦"]):
            types["情绪表达"] += 1
        if any(w in m for w in ["来","去","到","给","发","送","拿","带"]):
            types["行动安排"] += 1
    results["msg_types"] = {k: round(v/total, 2) for k, v in types.items()}

    # === 7. 常用短语 ===
    bigrams = Counter()
    for m in msgs:
        if len(m) >= 4:
            for i in range(len(m)-1):
                bigrams[m[i:i+2]] += 1
    common_bigrams = [(bg, c) for bg, c in bigrams.most_common(30) if c > 50]
    results["common_bigrams"] = common_bigrams[:20]

    # === 8. 互动模式 ===
    ask_back = sum(1 for m in msgs if ("你" in m and ("呢" in m or "吗" in m or "吧" in m) and len(m) < 15))
    results["ask_back_rate"] = round(ask_back / total, 2)  # 回复后反问比例

    # === 9. 语气分析 ===
    casual = sum(1 for m in msgs if any(w in m for w in ["哈哈","嘿","嘛","啦","咯","滴","呀"]))
    polite = sum(1 for m in msgs if any(w in m for w in ["谢谢","请","麻烦","不好意思"]))
    results["casual_rate"] = round(casual / total, 2)
    results["polite_rate"] = round(polite / total, 2)

    return results


def generate_prompt(results):
    lines = []
    lines.append("## 说话风格深度分析\n")

    lines.append(f"### 基本信息")
    lines.append(f"- 平均消息长度: {results['avg_len']} 字")
    lines.append(f"- 短回复(<5字)占比: {results['short_ratio']*100:.0f}%")
    lines.append(f"- 长回复(>20字)占比: {results['long_ratio']*100:.0f}%")
    lines.append(f"- 回复后反问的比例: {results['ask_back_rate']*100:.0f}%")
    lines.append(f"- 随意口语比例: {results['casual_rate']*100:.0f}%")
    lines.append(f"- 礼貌用语比例: {results['polite_rate']*100:.0f}%")
    lines.append("")

    lines.append(f"### 消息类型分布")
    for t, r in results["msg_types"].items():
        lines.append(f"- {t}: {r*100:.0f}%")
    lines.append("")

    lines.append(f"### 高频词汇 Top 15")
    lines.append(", ".join([w for w, _ in results["top_words"][:15]]))
    lines.append("")

    lines.append(f"### 最爱用的表情")
    lines.append(", ".join([f"{e}({c}次)" for e, c in results["top_emojis"][:10]]))
    lines.append("")

    lines.append(f"### 句尾习惯")
    lines.append(", ".join([f"'{e}'({c}次)" for e, c in results["top_endings"]]))
    lines.append("")

    lines.append(f"### 常见开头")
    lines.append(", ".join([f"'{o}'" for o, _ in results["top_openings"]]))
    lines.append("")

    lines.append(f"### 常用短语")
    lines.append(", ".join([f"'{bg}'" for bg, _ in results["common_bigrams"][:15]]))
    lines.append("")

    lines.append("## 核心人格特征总结")
    lines.append(f"- 你说话非常简短({results['avg_len']}字/条)，是典型的微信聊天风格")
    lines.append(f"- 你{'' if results['casual_rate'] > 0.3 else '不太'}随意，语气{'轻松口语化' if results['casual_rate'] > 0.2 else '比较直接'}")
    lines.append(f"- 你{'经常' if results['ask_back_rate'] > 0.3 else '有时'}回复后会反问对方")
    if results['emoji_usage_rate'] > 0.3:
        lines.append(f"- 你经常使用微信表情(主要是{', '.join([e for e,_ in results['top_emojis'][:5]])})")
    if results['short_ratio'] > 0.4:
        lines.append(f"- 你{results['short_ratio']*100:.0f}%的回复都非常简短(≤5字)，常见如'好的'、'OK'、'嗯'")
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 50)
    print("  深度聊天记录分析")
    print("=" * 50)

    msgs = load()
    print(f"消息总数: {len(msgs)}")

    results = analyze(msgs)

    prompt = generate_prompt(results)
    print("\n" + prompt)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\n[已保存] {OUTPUT}")


if __name__ == "__main__":
    import jieba
    main()
