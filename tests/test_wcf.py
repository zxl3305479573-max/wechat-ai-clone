"""测试 WeChatFerry 能否在你的微信4.x上工作。"""
from wcferry import Wcf, WxMsg

print("初始化 WCF...")
wcf = Wcf()

print("连接微信...")
wcf.connect()
print("连接成功!")

print("获取自己信息...")
info = wcf.get_user_info()
print(f"  自己: {info}")

print("\n获取联系人列表...")
contacts = wcf.get_contacts()
print(f"  共 {len(contacts)} 个联系人")
for c in contacts[:5]:
    name = c.get("name", "")
    wxid = c.get("wxid", "")
    print(f"  {name} ({wxid})")

print("\n开始监听消息... (Ctrl+C 停止)")
print("让朋友发一条消息来测试\n")

def on_msg(msg: WxMsg):
    if msg.from_self:
        return
    print(f"\n>>> [{msg.sender}] {msg.content}")

wcf.callback = on_msg
try:
    wcf.loop_forever()
except KeyboardInterrupt:
    print("\n停止")
