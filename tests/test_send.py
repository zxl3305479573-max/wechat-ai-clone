"""测试：通过 Ctrl+F 搜索联系人并发送消息。"""
import time, win32gui, win32con, win32clipboard, pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

# 找微信
result = []
def cb(h, _):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if "微信" in t:
            r = win32gui.GetWindowRect(h)
            w, h_ = r[2]-r[0], r[3]-r[1]
            result.append((h, r, w, h_))
    return True
win32gui.EnumWindows(cb, None)
result.sort(key=lambda x: x[2]*x[3], reverse=True)
hwnd, rect, w, h = result[0]

print(f"微信: {w}x{h}")

# 激活窗口
try:
    win32gui.SetForegroundWindow(hwnd)
except:
    pass
time.sleep(0.3)

# 测试1: 搜索文件传输助手
target = "文件传输助手"
msg = "这是一条测试消息 - AI机器人"

print(f"\n[测试] 发送到: {target}")
print(f"  消息: {msg}")

# Ctrl+F
pyautogui.hotkey("ctrl", "f")
time.sleep(0.4)

# 清空搜索框
pyautogui.hotkey("ctrl", "a")
time.sleep(0.05)

# 输入联系人名
pyautogui.write(target, interval=0.03)
time.sleep(0.6)

# 按回车打开
pyautogui.press("enter")
time.sleep(0.4)

title = win32gui.GetWindowText(hwnd)
print(f"  打开后标题: '{title}'")

# 点输入框
ix = (rect[0] + rect[2]) // 2
iy = rect[3] - 80
pyautogui.click(ix, iy)
time.sleep(0.15)

# 粘贴
try:
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(msg, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
except:
    pass

pyautogui.hotkey("ctrl", "v")
time.sleep(0.1)
pyautogui.press("enter")

print("  [完成] 检查文件传输助手是否收到消息")
