"""微信 AI 分身 — 全自动回复机器人。
依赖: CipherTalk (API读消息) + DeepSeek (AI回复) + pyautogui (发送)
"""
import sys, os, time, re, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import win32gui, win32con, win32clipboard
import pyautogui
from llm import ChatAgent

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

API = "http://127.0.0.1:5031/v1"


class WxBot:
    def __init__(self):
        self.agent = ChatAgent()
        self.hwnd = None
        self.replied = set()
        self.sent_texts = {}

    def _api(self, path):
        try:
            with urllib.request.urlopen(f"{API}{path}", timeout=5) as r:
                return json.loads(r.read().decode())
        except:
            return None

    def _find_wechat(self):
        result = []
        def cb(h, _):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if "微信" in t:
                    r = win32gui.GetWindowRect(h)
                    result.append((h, r[2]-r[0], r[3]-r[1]))
            return True
        win32gui.EnumWindows(cb, None)
        if result:
            result.sort(key=lambda x: x[1]*x[2], reverse=True)
            self.hwnd = result[0][0]
            return True
        return False

    def _send(self, name, text):
        if not self.hwnd:
            return False
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except:
            pass
        time.sleep(0.2)

        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.write(name, interval=0.03)
        time.sleep(0.8)
        pyautogui.press("down")
        time.sleep(0.1)
        pyautogui.press("down")
        time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(0.5)

        rect = win32gui.GetWindowRect(self.hwnd)
        pyautogui.click((rect[0]+rect[2])//2, rect[3]-80)
        time.sleep(0.1)

        try:
            wc = win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except:
            pass

        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(0.15)
        return True

    def run(self):
        print("\n" + "=" * 50)
        print("  微信 AI 分身")
        print("=" * 50)

        if not self._api("/health"):
            print("[错误] CipherTalk API 不可用，请先启动 CipherTalk")
            return
        print("[CipherTalk] OK")

        has_win = self._find_wechat()
        print(f"[微信] {'OK' if has_win else '未找到'}")
        if not has_win:
            return

        print(f"[AI] {self.agent.model}")
        print(f"[人格] {len(self.agent.system_prompt)} 字")

        # 建立基线
        baseline = {}
        data = self._api("/sessions")
        if data:
            for s in data["data"]["sessions"]:
                uname = s.get("username", "")
                if uname:
                    mdata = self._api(f"/messages?sessionId={uname}&limit=1")
                    if mdata and mdata.get("success"):
                        msgs = mdata["data"]["messages"]
                        baseline[uname] = int(msgs[0].get("localId", 0)) if msgs else 0

        print(f"\n监听中... (Ctrl+C 停止)\n")

        try:
            while True:
                data = self._api("/sessions")
                if not data:
                    time.sleep(3)
                    continue

                for s in data["data"]["sessions"]:
                    username = s.get("username", "")
                    display = s.get("displayName", "") or username
                    stype = s.get("sessionType", "")

                    if stype == "group" or int(s.get("unreadCount", 0)) <= 0:
                        continue

                    last_id = baseline.get(username, 0)
                    mdata = self._api(f"/messages?sessionId={username}&limit=5")
                    if not mdata or not mdata.get("success"):
                        continue

                    new_in = [m for m in mdata["data"]["messages"]
                              if m.get("direction") == "in" and int(m.get("localId", 0)) > last_id]

                    if not new_in:
                        continue

                    latest = new_in[0]
                    lid = int(latest.get("localId", 0))
                    content = latest.get("parsedContent", "")

                    if not content or lid in self.replied:
                        continue

                    baseline[username] = lid
                    clean = self._clean(content)
                    if clean == self.sent_texts.get(username):
                        continue

                    print(f"\n[{display}] {clean[:60]}{'...' if len(clean)>60 else ''}")
                    reply = self.agent.chat(display, clean)
                    print(f"  -> {reply[:60]}{'...' if len(reply)>60 else ''}")

                    ok = self._send(display, reply)
                    if not ok:
                        short = username.split("@")[0] if "@" in username else username
                        if short != display:
                            ok = self._send(short, reply)

                    if ok:
                        self.replied.add(lid)
                        self.sent_texts[username] = self._clean(reply)

                print(".", end="", flush=True)
                time.sleep(3)

        except KeyboardInterrupt:
            print("\n[停止]")

    def _clean(self, text):
        text = text.strip()
        text = re.sub(r'^\d{1,2}:\d{2}\s*', '', text)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        return text


if __name__ == "__main__":
    WxBot().run()
