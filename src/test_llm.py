"""测试 LLM 人格分身 —— 模拟聊天，不用微信。"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))

from llm import ChatAgent


def test():
    print("=" * 50)
    print("  AI 分身测试（模拟微信聊天）")
    print("  输入 /exit 退出, /clear 清空历史")
    print("=" * 50)

    agent = ChatAgent()
    print(f"\n[模型] {agent.model}")
    print(f"[风格] 已加载 {len(agent.system_prompt)} 字人格描述\n")

    contact = "测试朋友"

    # 预设测试对话
    test_msgs = [
        "在吗？",
        "晚上吃什么",
        "周末有什么安排",
        "明天要不要一起去打球",
        "最近怎么样",
    ]

    print("=== 快速测试 ===\n")
    for msg in test_msgs:
        reply = agent.chat(contact, msg)
        print(f"朋友: {msg}")
        print(f"我:   {reply}\n")

    # 交互模式
    print("=== 交互模式（输入消息开始聊天） ===")
    while True:
        try:
            user_input = input("\n朋友: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/clear":
            agent.clear_history(contact)
            print("[历史已清空]")
            continue

        reply = agent.chat(contact, user_input)
        print(f"我:   {reply}")


if __name__ == "__main__":
    test()
