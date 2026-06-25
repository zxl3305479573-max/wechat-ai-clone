"""微信4.x解密数据库 → 导出聊天记录 + 提取本人消息。"""
import json
import sqlite3
import zlib
import time
import yaml
from pathlib import Path
from collections import defaultdict

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

# 从配置文件读取路径
_source_db = ""
_output_dir = "./data/chat_records"
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _source_db = cfg.get("data", {}).get("source_db", "")
    _output_dir = cfg.get("data", {}).get("records_dir", _output_dir)

DB_DIR = Path(_source_db) if _source_db else Path(".")
OUTPUT = Path(_output_dir)
OUTPUT.mkdir(parents=True, exist_ok=True)

# 在微信数据库中，你的 sender_id 需要通过 Name2Id 表查找
# 运行时会自动打印找到的本人 wxid
MY_SENDER_ID = None  # 设为 None 则自动查找；或手动指定 rowid


def load_name2id(msg_db_dir: Path) -> dict:
    name2id = {}
    for db_path in sorted(msg_db_dir.glob("message_*.db")):
        if db_path.name in ("message_fts.db", "message_resource.db"):
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT rowid, user_name FROM Name2Id")
            for row in cur.fetchall():
                name2id[row[0]] = row[1]
            conn.close()
        except Exception:
            pass
    return name2id


def load_contacts() -> dict:
    db = DB_DIR / "contact" / "contact.db"
    contacts = {}
    if db.exists():
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        for table in ["contact", "stranger"]:
            try:
                cur.execute(f"SELECT username, remark, nick_name FROM {table}")
                for row in cur.fetchall():
                    wxid, remark, nickname = row[0] or "", row[1] or "", row[2] or ""
                    contacts[wxid] = remark or nickname
            except Exception:
                pass
        conn.close()
    return contacts


def decode_text(content, compress, wcdb_ct) -> str:
    text = ""
    if wcdb_ct == 0 and content:
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)
    if not text and compress:
        try:
            text = zlib.decompress(compress).decode("utf-8", errors="ignore")
        except Exception:
            pass
    if not text and isinstance(content, bytes) and content:
        try:
            text = zlib.decompress(content).decode("utf-8", errors="ignore")
        except Exception:
            text = content.decode("utf-8", errors="ignore")
    return text.strip()


def is_valid_text(text: str) -> bool:
    if not text or len(text) < 1 or len(text) > 500:
        return False
    if text.startswith("<") and text.endswith(">") and len(text) > 30:
        return False
    skip = ["你收到一条", "撤回了一条", "邀请你加入", "修改了群名",
            "[链接]", "[视频]", "[图片]", "[语音]", "[动画表情]",
            "[文件]", "[聊天记录]", "[小程序]", "[视频号]", "[引用]"]
    for s in skip:
        if text == s or text.startswith(s):
            return False
    return True


def main():
    print("=" * 50)
    print("  微信4.x 聊天记录导出")
    print("=" * 50)
    print(f"  数据源: {DB_DIR}")
    print(f"  输出: {OUTPUT}")

    contacts = load_contacts()
    print(f"[联系人] {len(contacts)} 个")

    msg_dir = DB_DIR / "message"
    name2id = load_name2id(msg_dir)
    print(f"[Name2Id] {len(name2id)} 个")

    # 自动查找本人 sender_id（如果未手动指定）
    sender_id = MY_SENDER_ID
    if sender_id is None and name2id:
        # 常见情况：rowid 较小的那个通常是本人
        # 用户需要在配置中指定正确的值
        print("[警告] 未指定 MY_SENDER_ID，将导出所有消息")
        print("  提示：在 decrypt_db.py 顶部设置 MY_SENDER_ID 为你的 rowid")
        print(f"  可用的 Name2Id 映射（前10个）:")
        for rid, name in sorted(name2id.items())[:10]:
            print(f"    rowid={rid} -> {name}")

    my_messages = []
    all_messages = []

    for db_path in sorted(msg_dir.glob("message_*.db")):
        if db_path.name in ("message_fts.db", "message_resource.db"):
            continue

        print(f"  {db_path.name}...")
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
            all_tables = [r[0] for r in cur.fetchall()]
            msg_tables = [t for t in all_tables if len(t) == 36]

            for table in msg_tables:
                try:
                    cur.execute(f'SELECT local_type, real_sender_id, create_time, message_content, compress_content, WCDB_CT_message_content FROM "{table}" ORDER BY sort_seq DESC LIMIT 500')

                    for row in cur.fetchall():
                        local_type, s_id, ts, content, compress, wcdb_ct = row
                        if local_type != 1:
                            continue

                        text = decode_text(content, compress, wcdb_ct)
                        if not is_valid_text(text):
                            continue

                        try:
                            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))
                        except Exception:
                            time_str = str(ts)

                        msg_entry = {
                            "content": text,
                            "time": time_str,
                        }

                        if sender_id is not None and s_id == sender_id:
                            my_messages.append(msg_entry)
                        elif sender_id is None:
                            all_messages.append({
                                **msg_entry,
                                "sender_id": s_id,
                            })
                except Exception:
                    pass
            conn.close()
        except Exception as e:
            print(f"    错误: {e}")

    # 保存本人消息
    if sender_id is not None:
        my_path = OUTPUT / "my_messages.json"
        with open(my_path, "w", encoding="utf-8") as f:
            json.dump(my_messages, f, ensure_ascii=False, indent=2)
        print(f"\n[本人消息] {len(my_messages)} 条 -> {my_path}")
    else:
        all_path = OUTPUT / "all_messages.json"
        with open(all_path, "w", encoding="utf-8") as f:
            json.dump(all_messages, f, ensure_ascii=False, indent=2)
        print(f"\n[所有消息] {len(all_messages)} 条 -> {all_path}")

    # 打印样例
    sample_path = OUTPUT / "my_messages_sample.txt"
    with open(sample_path, "w", encoding="utf-8") as f:
        if sender_id is not None:
            f.write(f"本人消息样例 (共{len(my_messages)}条)\n{'='*40}\n\n")
            for m in my_messages[-30:]:
                f.write(f"[{m['time']}] {m['content']}\n")
        else:
            f.write(f"所有消息样例 (共{len(all_messages)}条)\n{'='*40}\n\n")
            for m in all_messages[-30:]:
                f.write(f"[{m['time']}] {m['content']}\n")
    print(f"[样例] {sample_path}")

    print("\n[完成]")


if __name__ == "__main__":
    main()
