"""诊断脚本：逐步测试微信自动化每个环节，找出问题。"""
import time
import win32gui
import win32con
import win32clipboard
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

print("=" * 50)
print("  微信自动化诊断")
print("=" * 50)
print()
print("【提示】确保微信已打开且窗口可见，正在自动诊断...")
time.sleep(2)


def clip_read():
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

# Step 1: Find WeChat window
print("\n[Step 1] 查找微信窗口...")
hwnd = win32gui.FindWindow(None, "微信")
if not hwnd:
    print("  FAIL: 未找到标题为'微信'的窗口")
    exit()
print(f"  OK: hwnd={hwnd}")

title = win32gui.GetWindowText(hwnd)
print(f"  窗口标题: '{title}'")

rect = win32gui.GetWindowRect(hwnd)
print(f"  窗口位置: left={rect[0]} top={rect[1]} right={rect[2]} bottom={rect[3]}")
print(f"  窗口大小: {rect[2]-rect[0]} x {rect[3]-rect[1]}")

# Step 2: Activate window
print("\n[Step 2] 激活窗口...")
placement = win32gui.GetWindowPlacement(hwnd)
print(f"  当前状态: show_cmd={placement[1]}")
if placement[1] == win32con.SW_SHOWMINIMIZED:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.5)
    status = "已还原"
else:
    status = "已正常"
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.5)
print(f"  OK: {status}")

# Step 3: Attempt to copy chat content
print("\n[Step 3] 复制聊天内容...")
# Click on chat message area (center of window, a bit above center)
center_x = (rect[0] + rect[2]) // 2
center_y = (rect[1] + rect[3]) // 2 - 50
print(f"  点击消息区: ({center_x}, {center_y})")
pyautogui.click(center_x, center_y)
time.sleep(0.3)

# Try Ctrl+A to select all
pyautogui.hotkey("ctrl", "a")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "c")
time.sleep(0.3)

text = clip_read()
print(f"  复制结果: {len(text)} 字符")
print(f"  前300字: {text[:300]}")
print()

# Step 4: Analyze the copied text
print("[Step 4] 解析消息...")
lines = text.strip().split("\n")
print(f"  总行数: {len(lines)}")

# Show lines that are likely messages
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped and len(stripped) > 1:
        is_time = bool(__import__('re').match(r'^\d{1,2}:\d{2}$', stripped))
        marker = " [时间]" if is_time else ""
        print(f"    L{i}: '{stripped[:60]}'{marker}")

# Step 5: Test keyboard navigation
print("\n[Step 5] 测试键盘导航...")
# Esc to go to chat list
pyautogui.press("esc")
time.sleep(0.3)
pyautogui.press("esc")
time.sleep(0.3)
print("  按了 2 次 Esc")
time.sleep(0.3)

# Click first chat
first_x = rect[0] + 120
first_y = rect[1] + 85
print(f"  点击第一个聊天: ({first_x}, {first_y})")
pyautogui.click(first_x, first_y)
time.sleep(0.4)

title_after = win32gui.GetWindowText(hwnd)
print(f"  点击后标题: '{title_after}'")

# Press Down to test navigation
print("  按 Down 键...")
pyautogui.press("down")
time.sleep(0.3)
title_down = win32gui.GetWindowText(hwnd)
print(f"  Down后标题: '{title_down}'")

# Press Enter to open chat
print("  按 Enter 打开聊天...")
pyautogui.press("enter")
time.sleep(0.5)
title_enter = win32gui.GetWindowText(hwnd)
print(f"  Enter后标题: '{title_enter}'")

print("\n" + "=" * 50)
print("  诊断完成！")
print("  请把以上输出发给我，我来分析问题。")
print("=" * 50)
