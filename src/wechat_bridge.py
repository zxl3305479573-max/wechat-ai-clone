"""微信 AI 分身 v1.0 —— 双击复制消息 + 键盘发送。经过坐标验证。"""
import time
import re
import win32gui
import win32con
import win32clipboard
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08


class NativeWeChatBridge:
    def __init__(self):
        self.agent = None
        self.hwnd = None
        self.replied = {}     # contact -> msg we replied to
        self.my_replies = {}  # contact -> last reply we sent
        self.scan_count = 0

    def set_agent(self, agent):
        self.agent = agent

    # ── 窗口 ────────────────────────────────

    def _find_wechat(self):
        result = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if "微信" in t or "WeChat" in t:
                    r = win32gui.GetWindowRect(hwnd)
                    w, h = r[2] - r[0], r[3] - r[1]
                    result.append((hwnd, w, h, r))
            return True
        win32gui.EnumWindows(cb, None)
        if result:
            result.sort(key=lambda x: x[1] * x[2], reverse=True)
            self.hwnd = result[0][0]
            return True
        self.hwnd = win32gui.FindWindow(None, "微信")
        return bool(self.hwnd)

    def _ensure_visible(self):
        if not self.hwnd and not self._find_wechat():
            return False
        r = win32gui.GetWindowRect(self.hwnd)
        w, h = r[2] - r[0], r[3] - r[1]
        if w < 200 or h < 200 or r[0] < -2000:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWMAXIMIZED)
            time.sleep(0.5)
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except:
            pass
        time.sleep(0.3)
        return True

    # ── 剪贴板 ──────────────────────────────

    def _clip_read(self):
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return data
            win32clipboard.CloseClipboard()
        except:
            pass
        return ""

    def _clip_write(self, text):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except:
            pass

    def _clip_clear(self):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
        except:
            pass

    # ── 读取消息（验证过坐标的双击方案）─────

    def _read_last_msg(self):
        """双击消息气泡 -> Ctrl+C -> 返回消息文本。返回 (msg, is_from_other)。"""
        if not self.hwnd:
            return "", False

        rect = win32gui.GetWindowRect(self.hwnd)
        ww, wh = rect[2] - rect[0], rect[3] - rect[1]
        if ww < 200 or wh < 200:
            return "", False

        # 先清空剪贴板
        self._clip_clear()

        # 滚动到底部确保最后消息可见
        for _ in range(4):
            pyautogui.press("pagedown")
            time.sleep(0.03)

        # === 方法：双击消息气泡 ===
        # 根据测试验证：窗口右下区域的消息气泡可双击选中
        # 相对坐标: x≈窗口宽度的55%, y≈底部往上160px
        click_x = rect[0] + int(ww * 0.55)
        click_y = rect[1] + wh - 160

        pyautogui.doubleClick(click_x, click_y)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)

        text = self._clip_read()

        # 取消选中
        pyautogui.click(rect[0] + 300, rect[1] + 300)
        time.sleep(0.1)

        if not text or len(text) < 2:
            # 回退：试试更靠右边的坐标（对方的消息偏左）
            pyautogui.doubleClick(click_x - 80, click_y)
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            text = self._clip_read()
            pyautogui.click(rect[0] + 300, rect[1] + 300)
            time.sleep(0.1)

        text = text.strip() if text else ""

        # 判断是否对方发的：检查文本是否包含"我"（通常微信复制时自己消息有"我"标识）
        lines = text.split("\n")
        is_from_other = True  # 默认当作对方消息
        for line in lines[:3]:
            if line.strip() == "我":
                is_from_other = False
                break

        # 如果第一行就是"我"，去掉这行
        if lines and lines[0].strip() == "我" and len(lines) > 1:
            text = lines[1].strip()
        else:
            text = lines[0].strip() if lines else ""

        # 过滤明显不是聊天内容的东西
        if text and len(text) > 2:
            return text, is_from_other

        return "", False

    def _get_contact(self):
        title = win32gui.GetWindowText(self.hwnd)
        return title.replace(" - 微信", "").replace("微信", "").strip() or ""

    # ── 导航 ────────────────────────────────

    def _go_to_chat_list(self):
        self._ensure_visible()
        for _ in range(2):
            pyautogui.press("esc")
            time.sleep(0.15)

    def _select_chat(self, index):
        self._go_to_chat_list()
        rect = win32gui.GetWindowRect(self.hwnd)
        pyautogui.click(rect[0] + 120, rect[1] + 85)
        time.sleep(0.15)
        for _ in range(index):
            pyautogui.press("down")
            time.sleep(0.08)

    def _open_chat(self):
        pyautogui.press("enter")
        time.sleep(0.35)

    def _close_chat(self):
        pyautogui.press("esc")
        time.sleep(0.2)

    def _send_msg(self, text):
        self._ensure_visible()
        rect = win32gui.GetWindowRect(self.hwnd)
        ix = (rect[0] + rect[2]) // 2
        iy = rect[3] - 80
        pyautogui.click(ix, iy)
        time.sleep(0.12)
        self._clip_write(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(0.15)

    # ── 主入口 ───────────────────────────────

    def run(self):
        print("\n" + "=" * 50)
        print("  微信 AI 分身 v1.0")
        print("=" * 50)
        if not self._find_wechat():
            print("[错误] 未找到微信窗口")
            return
        if not self._ensure_visible():
            print("[错误] 无法激活微信")
            return
        print(f"[微信] 已连接")

        print("\n1. 回复所有人 | 2. 回复指定人 | 3. 命令行")
        m = input("选择 (1/2/3): ").strip() or "2"
        if m == "1":
            self._monitor_all()
        elif m == "2":
            self._monitor_one()
        else:
            self._manual()

    # ── 模式1 ────────────────────────────────

    def _monitor_all(self):
        n = int(input("扫描前几个联系人？(默认8): ").strip() or "8")
        print(f"\n[扫描] 前{n}个 | 间隔6秒 | Ctrl+C停止\n")
        try:
            while True:
                r = self._scan(n)
                self.scan_count += 1
                print(f"[第{self.scan_count}轮] 回复{r}人")
                time.sleep(6)
        except KeyboardInterrupt:
            print("\n[停止]")

    def _scan(self, n):
        replied = 0
        for i in range(n):
            try:
                self._select_chat(i)
                self._open_chat()
                contact = self._get_contact()
                if contact.startswith("gh_") or contact in ("微信团队", "微信支付"):
                    self._close_chat()
                    continue

                msg, is_other = self._read_last_msg()
                if msg and is_other:
                    clean = self._clean(msg)
                    if clean and clean != self.replied.get(contact) and clean != self.my_replies.get(contact):
                        print(f"\n[{contact}] {clean[:50]}{'...' if len(clean)>50 else ''}")
                        reply = self.agent.chat(contact, clean)
                        print(f"  -> {reply[:50]}{'...' if len(reply)>50 else ''}")
                        self._send_msg(reply)
                        self.replied[contact] = clean
                        self.my_replies[contact] = self._clean(reply)
                        replied += 1
                self._close_chat()
            except pyautogui.FailSafeException:
                raise
            except Exception as e:
                try:
                    self._close_chat()
                except:
                    pass
        return replied

    # ── 模式2 ────────────────────────────────

    def _monitor_one(self):
        contact = input("联系人备注名: ").strip()
        if not contact:
            return
        print(f"\n[监听] {contact} | Ctrl+C停止\n")
        self._ensure_visible()
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(contact, interval=0.03)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(0.4)

        try:
            while True:
                msg, is_other = self._read_last_msg()
                if msg and is_other:
                    clean = self._clean(msg)
                    if clean and clean != self.replied.get(contact) and clean != self.my_replies.get(contact):
                        print(f"\n[{contact}] {clean}")
                        reply = self.agent.chat(contact, clean)
                        print(f"  -> {reply}")
                        self._send_msg(reply)
                        self.replied[contact] = clean
                        self.my_replies[contact] = self._clean(reply)
                time.sleep(3)
        except KeyboardInterrupt:
            print("\n[停止]")

    # ── 模式3 ────────────────────────────────

    def _manual(self):
        contact = input("联系人备注名 (可选): ").strip()
        if contact:
            self._ensure_visible()
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.write(contact, interval=0.03)
            time.sleep(0.6)
            pyautogui.press("enter")

        print("\n[命令行] :exit | :open <名> | :send <内容>\n")
        while True:
            try:
                msg = input("对方: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not msg:
                continue
            if msg == ":exit":
                break
            if msg.startswith(":open "):
                self._ensure_visible()
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.4)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.write(msg[6:], interval=0.03)
                time.sleep(0.6)
                pyautogui.press("enter")
                continue
            if msg.startswith(":send "):
                self._send_msg(msg[6:])
                continue
            reply = self.agent.chat(contact or "朋友", msg)
            print(f"我:   {reply}")
            self._send_msg(reply)

    def _clean(self, text):
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^(今天|昨天|星期).*?\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        return text.strip()


def create_bridge():
    return NativeWeChatBridge()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from llm import ChatAgent

    bridge = NativeWeChatBridge()
    bridge.set_agent(ChatAgent())
    bridge.run()
