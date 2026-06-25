"""数据库消息监控器 —— 用密钥读加密DB，检测新消息，无需UI读取。"""
import json
import time
import hashlib
import yaml
from pathlib import Path
from sqlcipher3 import dbapi2

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

# 延迟加载，避免未配置时 import 就报错
_db_config = None


def _get_db_config():
    """懒加载数据库配置（首次调用时读取）。"""
    global _db_config
    if _db_config is not None:
        return _db_config
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {CONFIG_PATH}\n"
            f"请复制 config.example.yaml 为 config.yaml 并填入你的信息。"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    key = cfg.get("db_key", "")
    if not key:
        raise ValueError("请在 config.yaml 中设置 db_key（微信数据库解密密钥）")
    source_db = cfg.get("data", {}).get("source_db", "")
    if not source_db:
        raise ValueError("请在 config.yaml 中设置 data.source_db（解密后的微信数据库路径）")
    source_db_path = Path(source_db)
    _db_config = (
        key,
        source_db_path / "message",
        str(source_db_path / "contact" / "contact.db"),
    )
    return _db_config


class MessageMonitor:
    """从加密数据库实时读取新消息。"""

    def __init__(self):
        self.last_seen = {}  # contact_hash -> max local_id
        self.contact_map = {}  # Msg_hash -> contact_info
        self._load_contact_map()

    def _open_db(self, db_path):
        key, _, _ = _get_db_config()
        conn = dbapi2.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(f"PRAGMA key=\"x'{key}'\"")
        # WAL 模式：允许微信同时写入
        try:
            cur.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        return conn, cur

    def _load_contact_map(self):
        """从会话数据库和联系人数据库加载 hash -> 名字 的映射。"""
        import sqlite3
        _, msg_dir, contact_db = _get_db_config()
        # 1. 从 session.db 获取会话列表
        session_db = msg_dir.parent / "session" / "session.db"
        if session_db.exists():
            try:
                conn = sqlite3.connect(str(session_db))
                cur = conn.cursor()
                cur.execute("SELECT username, summary, last_sender_display_name FROM SessionTable")
                for row in cur.fetchall():
                    username, summary, display = row
                    # username 可能是 wxid 或 chatroom id
                    h = hashlib.md5((username or "").encode()).hexdigest()
                    self.contact_map[h] = {
                        "username": username or "",
                        "summary": summary or "",
                        "display": display or "",
                    }
                conn.close()
            except Exception:
                pass

        # 2. 从 contact.db 补全昵称
        if Path(contact_db).exists():
            try:
                conn = sqlite3.connect(contact_db)
                cur = conn.cursor()
                for table in ["contact", "stranger"]:
                    try:
                        cur.execute(f"SELECT username, remark, nick_name FROM {table}")
                        for row in cur.fetchall():
                            wxid, remark, nickname = row[0] or "", row[1] or "", row[2] or ""
                            h = hashlib.md5(wxid.encode()).hexdigest()
                            if h in self.contact_map:
                                self.contact_map[h]["display_name"] = remark or nickname
                    except Exception:
                        pass
                conn.close()
            except Exception:
                pass

        print(f"[数据库] 加载 {len(self.contact_map)} 个会话映射")

    def check_new_messages(self) -> list[dict]:
        """扫描所有消息数据库，返回新消息列表。"""
        _, msg_dir, _ = _get_db_config()
        new_msgs = []

        for db_path in sorted(msg_dir.glob("message_*.db")):
            if db_path.name in ("message_fts.db", "message_resource.db"):
                continue

            try:
                conn, cur = self._open_db(db_path)
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' AND length(name)=36")
                tables = [r[0] for r in cur.fetchall()]

                for table in tables:
                    contact_hash = table.replace("Msg_", "")

                    # 查最新 local_id
                    try:
                        cur.execute(f'SELECT MAX(local_id) FROM "{table}"')
                        max_id = cur.fetchone()[0] or 0

                        last_id = self.last_seen.get(contact_hash, 0)
                        if max_id <= last_id:
                            continue

                        # 有新消息，读取
                        cur.execute(f'''
                            SELECT local_id, local_type, real_sender_id, create_time, message_content, WCDB_CT_message_content
                            FROM "{table}"
                            WHERE local_id > {last_id} AND local_type = 1
                            ORDER BY local_id ASC
                        ''')

                        for row in cur.fetchall():
                            local_id, local_type, sender_id, ts, content, wcdb_ct = row

                            # 解析内容
                            text = ""
                            if wcdb_ct == 0 and content:
                                text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)

                            if not text or len(text) < 1:
                                continue

                            # 修正 last_seen
                            if local_id > self.last_seen.get(contact_hash, 0):
                                self.last_seen[contact_hash] = local_id

                            # 获取联系人信息
                            info = self.contact_map.get(contact_hash, {})
                            contact_name = info.get("display_name") or info.get("display") or info.get("username") or contact_hash[:16]
                            if contact_name.startswith("wxid_"):
                                # 没找到备注名，用 hash
                                contact_name = contact_hash[:12]

                            # 时间
                            try:
                                time_str = time.strftime("%H:%M", time.localtime(int(ts)))
                            except Exception:
                                time_str = ""

                            new_msgs.append({
                                "contact_hash": contact_hash,
                                "contact": contact_name,
                                "content": text.strip(),
                                "time": time_str,
                                "msg_id": local_id,
                                "sender_id": sender_id,
                            })

                        self.last_seen[contact_hash] = max_id

                    except Exception:
                        pass

                conn.close()
            except Exception:
                pass

        return new_msgs

    def mark_replied(self, contact_hash, msg_id):
        """标记某条消息已回复。"""
        # 确保 last_seen 至少到这里
        if msg_id > self.last_seen.get(contact_hash, 0):
            self.last_seen[contact_hash] = msg_id


if __name__ == "__main__":
    print("测试消息监控器...")
    monitor = MessageMonitor()

    print("\n开始监控（每5秒检查一次）...")
    try:
        while True:
            msgs = monitor.check_new_messages()
            for m in msgs:
                print(f"[{m['contact']}][{m['time']}] {m['content'][:60]}")
            if not msgs:
                print(".", end="", flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n停止")
