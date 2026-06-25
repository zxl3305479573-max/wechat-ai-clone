"""聊天记录预处理 —— 分析说话风格，生成 personality prompt。"""
import json
import re
import yaml
from pathlib import Path
from collections import Counter

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _get_data_dir():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return Path(cfg.get("data", {}).get("records_dir", "./data/chat_records"))
    return Path("./data/chat_records")


DATA_DIR = _get_data_dir()
RECORDS_FILE = DATA_DIR / "my_messages.json"


def load_my_messages():
    if not RECORDS_FILE.exists():
        print(f"文件不存在: {RECORDS_FILE}")
        return []
    with open(RECORDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [m["content"] for m in data if "content" in m]


def clean_messages(msgs: list[str]) -> list[str]:
    cleaned = []
    for msg in msgs:
        msg = msg.strip()
        if not msg or len(msg) < 1 or len(msg) > 200:
            continue
        # 去掉转发消息的 wxid 前缀
        msg = re.sub(r'^wxid_[a-z0-9]+:\s*\n?', '', msg)
        # 过滤纯乱码（中英文占比 < 50%）
        chinese = len(re.findall(r'[一-鿿]', msg))
        ascii_chars = len(re.findall(r'[a-zA-Z0-9]', msg))
        total = len(msg.replace(' ', ''))
        if total > 0 and (chinese + ascii_chars) / total < 0.5:
            continue
        cleaned.append(msg)
    return cleaned


def analyze_style(messages: list[str]) -> dict:
    if not messages:
        return {}
    import jieba
    total = len(messages)
    avg_len = round(sum(len(m) for m in messages) / total, 1)

    all_words = []
    for msg in messages:
        words = jieba.lcut(msg)
        all_words.extend([w for w in words if len(w) > 1])

    stop_words = {"哈哈", "嗯嗯", "哦哦", "啊啊", "呃呃", "呜呜", "喂喂",
                  "这个", "那个", "什么", "怎么", "为什么", "可以", "没有",
                  "就是", "然后", "但是", "因为", "所以", "如果", "的话",
                  "一个", "一下", "一点", "一直", "已经", "不是", "还是",
                  "觉得", "知道", "应该", "可能", "真的", "其实", "这样",
                  "你们", "我们", "他们", "她们"}
    filtered = [w for w in all_words if w not in stop_words]
    common = Counter(filtered).most_common(30)

    emoji_pat = re.compile(r'[\U0001F300-\U0001F9FF\U0001F600-\U0001F64F☀-➿✂-➰Ⓜ-\U0001F251‍☀-⛿✀-➿]')
    emoji_count = sum(1 for m in messages if emoji_pat.search(m))

    endings = Counter()
    for m in messages:
        last = m[-1]
        if last in "哈呢呀吧哦嘛啊啦滴咯的":
            endings[last] += 1
        elif last in "~～！!？?….":
            endings[last] += 1

    return {
        "total": total,
        "avg_len": avg_len,
        "top_words": [w for w, _ in common[:15]],
        "emoji_ratio": round(emoji_count / total, 2),
        "top_endings": [c for c, _ in endings.most_common(8)],
    }


def build_persona_prompt(style: dict, samples: list[str]) -> str:
    lines = []
    if style:
        lines.append("## 说话风格特征")
        if style.get("avg_len"):
            lines.append(f"- 平均消息长度: {style['avg_len']} 字")
        if style.get("top_words"):
            lines.append(f"- 高频词汇: {', '.join(style['top_words'][:10])}")
        if style.get("top_endings"):
            lines.append(f"- 常用句尾: {', '.join(style['top_endings'])}")
        if style.get("emoji_ratio", 0) > 0.03:
            lines.append("- 适度使用表情符号")
    if samples:
        lines.append("\n## 说话样例（来自真实聊天记录）")
        for m in samples[:10]:
            lines.append(f"- \"{m}\"")
    return "\n".join(lines)


def main():
    print("=" * 50)
    print("  聊天风格分析")
    print("=" * 50)

    raw = load_my_messages()
    print(f"原始消息: {len(raw)} 条")

    cleaned = clean_messages(raw)
    print(f"清洗后: {len(cleaned)} 条")

    style = analyze_style(cleaned)
    print(f"\n平均长度: {style.get('avg_len', 'N/A')} 字")
    print(f"高频词 Top 10: {style.get('top_words', [])[:10]}")
    print(f"常用句尾: {style.get('top_endings', [])}")
    print(f"表情比例: {style.get('emoji_ratio', 'N/A')}")

    # 选典型样例（中等长度消息）
    mid = [m for m in cleaned if 5 < len(m) < 30]
    samples = mid[-15:] if len(mid) > 15 else cleaned[-15:]

    prompt = build_persona_prompt(style, samples)

    profile = DATA_DIR / "style_profile.txt"
    profile.write_text(prompt, encoding="utf-8")
    print(f"\n风格描述 -> {profile}")

    cleaned_path = DATA_DIR / "my_messages_cleaned.json"
    with open(cleaned_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"清洗后消息 -> {cleaned_path} ({len(cleaned)} 条)")


if __name__ == "__main__":
    import jieba
    main()
