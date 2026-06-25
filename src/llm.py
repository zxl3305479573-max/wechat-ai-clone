"""DeepSeek API 封装 —— 带人格蒸馏的聊天补全。"""
import yaml
from pathlib import Path
from openai import OpenAI

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {CONFIG_PATH}\n"
            f"请复制 config.example.yaml 为 config.yaml 并填入你的信息。\n"
            f"  cp config.example.yaml config.yaml"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class ChatAgent:
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        cfg = self.config["deepseek"]

        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model = cfg["model"]
        self.max_tokens = cfg.get("max_tokens", 1024)
        self.temperature = cfg.get("temperature", 0.8)
        self.persona = self.config.get("persona", {})
        self.system_prompt = self._build_system_prompt()
        self.conversations: dict[str, list[dict]] = {}

    def _build_system_prompt(self) -> str:
        name = self.persona.get("name", "我")

        prompt = f"""你是{name}本人，在微信上和你的朋友聊天。永远不要暴露你是AI。

## 你的背景（内部知识，聊天时用自己的话自然表达，禁止照搬原文）

"""
        # 基本信息
        parts = []
        city = self.persona.get("city", "")
        school = self.persona.get("school", "")
        grade = self.persona.get("grade", "")
        age = self.persona.get("age", "")
        if city:
            parts.append(f"你在{city}")
        if school:
            parts.append(f"在{school}读书" + (f"，{grade}" if grade else ""))
        if age:
            parts.append(f"{age}出生")
        if parts:
            prompt += "，".join(parts) + "。\n"

        routine = self.persona.get("daily_routine", "")
        if routine:
            prompt += f"日常：{routine}\n"
        hobbies = self.persona.get("hobbies", "")
        if hobbies:
            prompt += f"爱好：{hobbies}\n"
        spots = self.persona.get("regular_spots", "")
        if spots:
            prompt += f"常去：{spots}\n"

        # 重要事实
        facts = self.persona.get("facts", [])
        if facts:
            prompt += "\n个人经历（用自己的话自然表达，不要逐字背诵）：\n"
            for f in facts:
                if f.strip():
                    prompt += f"  {f.strip()}\n"

        prompt += """
⚠️ 以上是你的背景知识，不是回复模板！聊天时用自己的话自然说出来。
根据对方是谁选择性透露信息，普通朋友不用说得太详细。

## 说话风格
"""
        # 从配置的数据目录加载风格文件
        data_dir = self.config.get("data", {}).get("records_dir", "./data/chat_records")
        style_path = Path(data_dir) / "style_profile.txt"
        if style_path.exists():
            style_text = style_path.read_text(encoding="utf-8")
            prompt += style_text

        prompt += f"""

## 规则
- 你是{name}本人，回复基于真实信息，不编造
- 回复简短（通常不超过20字），口语化，适当用表情
- 聊到个人话题时自然回应，不要念文档
- 不知道的就说"不太清楚"
"""
        return prompt

    def chat(self, contact: str, incoming_msg: str) -> str:
        if contact not in self.conversations:
            self.conversations[contact] = [
                {"role": "system", "content": self.system_prompt}
            ]

        history = self.conversations[contact]
        history.append({"role": "user", "content": incoming_msg})

        # 保留最近 20 轮
        if len(history) > 41:
            history = [history[0]] + history[-40:]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=history,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            reply = resp.choices[0].message.content.strip()
        except Exception as e:
            reply = f"[错误: {e}]"

        history.append({"role": "assistant", "content": reply})
        self.conversations[contact] = history
        return reply

    def clear_history(self, contact: str):
        self.conversations.pop(contact, None)
