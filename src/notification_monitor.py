"""Windows 系统通知监听 —— 捕获微信新消息通知，无需任何第三方工具。

原理：Windows 10/11 的通知会短暂显示一个 UWP 弹窗窗口，
通过定时枚举顶层窗口来检测微信通知的出现和内容。
"""

import time
import re
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Windows 常量
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
GW_HWNDNEXT = 2
GW_CHILD = 5


def get_window_text(hwnd):
    """获取窗口标题文本。"""
    length = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 2)
    user32.SendMessageW(hwnd, WM_GETTEXT, length + 2, ctypes.byref(buf))
    return buf.value


def get_class_name(hwnd):
    """获取窗口类名。"""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def find_notification_windows():
    """枚举所有顶层窗口，寻找微信通知窗口。"""
    results = []

    def enum_callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            title = get_window_text(hwnd)
            cls = get_class_name(hwnd)
            if title and len(title) > 2:
                results.append((hwnd, title, cls))
        return True

    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(cb(enum_callback), 0)
    return results


def parse_wechat_notification(title):
    """从微信通知标题解析发送者和消息内容。

    微信通知格式（Windows通知中心）:
    - "联系人名: 消息内容"
    - "联系人名" (只有名字的可能是有图片/语音)
    - "微信" (多条消息聚合)
    - "[X条新消息]" (来自不同聊天的聚合)
    """
    # 跳过聚合通知
    if "条新消息" in title or title == "微信":
        return None

    # 尝试解析 "联系人: 消息" 格式
    match = re.match(r'^(.+?)[：:]\s*(.+)$', title)
    if match:
        contact = match.group(1).strip()
        content = match.group(2).strip()
        if contact and content and contact != "微信":
            return {"contact": contact, "content": content}

    # 如果只有名字（无消息文本），可能是图片/表情
    if len(title) > 1 and len(title) < 20 and ":" not in title and "：" not in title:
        return {"contact": title.strip(), "content": "[非文本消息]"}

    return None


class NotificationWatcher:
    """监控微信通知。"""

    # WeChat 4.x 通知窗口的类名可能是:
    # - Windows.UI.Core.CoreWindow (UWP通知)
    # - ApplicationFrameWindow
    # - Qt51514... (Qt通知)
    WECHAT_NOTIFY_CLASSES = [
        "Windows.UI.Core.CoreWindow",
        "ApplicationFrameWindow",
    ]

    def __init__(self):
        self.seen_titles = set()
        self.last_check_time = time.time()

    def check(self) -> list[dict]:
        """检查是否有新的微信通知，返回新消息列表。"""
        windows = find_notification_windows()
        new_msgs = []
        now = time.time()

        for hwnd, title, cls in windows:
            # 排除已知非微信窗口
            if cls in ("Shell_TrayWnd", "NotifyIconOverflowWindow", "Progman", "WorkerW"):
                continue

            # 检查是否是微信相关
            is_wechat = any(kw in title for kw in [
                "微信", "WeChat", "Weixin", "微信团队"
            ])

            if not is_wechat:
                # 也检查类名
                is_wechat = cls in self.WECHAT_NOTIFY_CLASSES

            if not is_wechat:
                continue

            # 去重：同一标题短时间内不重复
            key = f"{title}_{cls}"
            if key in self.seen_titles:
                continue

            self.seen_titles.add(key)

            # 清理旧记录
            if len(self.seen_titles) > 200:
                self.seen_titles = set(list(self.seen_titles)[-100:])

            result = parse_wechat_notification(title)
            if result:
                new_msgs.append(result)
                print(f"  [通知] {result['contact']}: {result['content'][:50]}")

        self.last_check_time = now

        # 定期清理旧记录
        if len(self.seen_titles) > 500:
            self.seen_titles.clear()

        return new_msgs


if __name__ == "__main__":
    print("微信通知监听器")
    print("监听中... (Ctrl+C 停止)")
    print("现在用另一个设备给此微信号发一条消息测试\n")

    watcher = NotificationWatcher()

    # 先获取当前所有窗口的 baseline
    watcher.seen_titles = {f"{t}_{c}" for _, t, c in find_notification_windows() if t}

    try:
        while True:
            msgs = watcher.check()
            for m in msgs:
                print(f"\n>>> [{m['contact']}] {m['content']}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止")
