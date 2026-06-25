"""网格扫描：找到微信消息气泡的精确坐标。"""
import time
import win32gui
import win32con
import win32clipboard
import pyautogui

pyautogui.FAILSAFE = False  # 暂时关闭防触发角，避免干扰
pyautogui.PAUSE = 0.05

print("准备: 打开微信和一个有聊天记录的对话 | 3秒后开始...")
time.sleep(3)

hwnd = win32gui.FindWindow(None, "微信")
if not hwnd:
    print("未找到微信！")
    exit()

rect = win32gui.GetWindowRect(hwnd)
rx, ry, rw, rh = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
print(f"窗口: ({rx},{ry}) {rw}x{rh}")

# 滚动到底部
try:
    win32gui.SetForegroundWindow(hwnd)
except:
    pass
time.sleep(0.2)
for _ in range(8):
    pyautogui.press("pagedown")
    time.sleep(0.03)
time.sleep(0.3)

# 消息区域估算：
# 左侧列表: 0~260px
# 消息区: 260~rw
# 顶部栏: 0~55px
# 输入区: rh-130~rh
# 消息气泡区: x=280~rw-20, y=60~rh-140

def try_copy(x, y, method):
    """尝试在(x,y)复制文本，返回是否成功。"""
    # 先把剪贴板清掉
    try:
        wc = win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
    except:
        pass

    if method == "right":
        pyautogui.click(x, y, button="right")
        time.sleep(0.3)
        # 微信右键菜单"复制"通常是第2或第3项
        pyautogui.press("down")
        time.sleep(0.08)
        pyautogui.press("down")
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(0.2)
    elif method == "drag":
        pyautogui.moveTo(x - 80, y)
        pyautogui.dragTo(x + 80, y, duration=0.15)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)
    elif method == "double":
        pyautogui.doubleClick(x, y)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)

    # 读剪贴板
    text = ""
    try:
        wc = win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except:
        pass

    pyautogui.click(rx + 300, ry + 300)  # 取消选中
    time.sleep(0.05)

    # 检查结果
    text = text.strip()
    if not text:
        return "空"
    if "python" in text.lower() or "quick_test" in text or "C:\\" in text:
        return "旧"
    if len(text) < 2:
        return "短"
    return f"新!({len(text)}字)"

# 扫描消息底部区域
print("\n=== 扫描消息底部 (y=rh-180 到 rh-100, x=280 到 rw-20) ===")
print(f"  消息区x范围: {rx+280} - {rx+rw-20}")
print(f"  消息区y范围: {ry+rh-180} - {ry+rh-100}")

for y_offset in range(-80, 40, 15):
    y = ry + rh + y_offset  # 从底部往上
    for x_offset in range(280, rw - 20, 80):
        x = rx + x_offset
        result = try_copy(x, y, "right")
        if "新" in result:
            print(f"  HIT! ({x}, {y}) -> {result}")
        # 只试前几个坐标，避免太慢

# 重点测试几个位置
print("\n=== 精确测试 ===")
test_points = [
    # (x相对窗口, y相对底部), 说明
    (350, -160, "右下-对方消息"),
    (500, -160, "右中"),
    (650, -160, "右右-自己消息"),
    (300, -140, "偏左"),
    (400, -100, "中偏下"),
]

for x_off, y_off, desc in test_points:
    x = rx + x_off
    y = ry + rh + y_off
    for method in ["right", "double", "drag"]:
        result = try_copy(x, y, method)
        if "新" in result:
            print(f"  HIT! ({x},{y}) [{desc}] {method} -> {result}")
            break

print("\n[完成] 如果有 HIT! 说明找到消息气泡了")
pyautogui.FAILSAFE = True
