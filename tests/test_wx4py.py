from wx4py import WeChatClient

wx = WeChatClient()
wx.connect()
print("连接成功!")

# 测试1: 向文件传输助手发消息
print("\n[测试1] 发送消息到文件传输助手...")
try:
    wx.chat_window.send_to("文件传输助手", "测试消息 - wx4py", target_type="contact")
    print("  发送成功!")
except Exception as e:
    print(f"  发送失败: {e}")

# 测试2: 读取聊天记录
print("\n[测试2] 读取文件传输助手聊天记录...")
try:
    msgs = wx.chat_window.get_chat_history("文件传输助手", max_count=5)
    print(f"  获取到 {len(msgs)} 条消息")
    for m in msgs:
        content = str(m.get("content", ""))[:60]
        is_self = m.get("is_self", False)
        print(f"  [{'自己' if is_self else '对方'}] {content}")
except Exception as e:
    print(f"  读取失败: {e}")
