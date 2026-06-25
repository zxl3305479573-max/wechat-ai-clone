# Watchat-Bot — 微信 AI 分身

让你的微信拥有 AI 自动回复能力。支持多种消息读取方案，使用 DeepSeek / OpenAI 兼容 API 驱动，带个人风格蒸馏。

## ✨ 特性

- 🤖 **AI 驱动的自动回复** — 接入 DeepSeek / OpenAI 兼容 API
- 🎭 **人格蒸馏** — 分析你的聊天记录，模仿你的说话风格
- 🔌 **多种消息读取方案**：
  - **CipherTalk API** — 通过本地 API 读取微信消息（推荐）
  - **桌面自动化** — 通过 pyautogui 操控微信窗口
  - **数据库直读** — 直接从微信加密数据库读取（需要解密密钥）
  - **系统通知监听** — 通过 Windows 通知捕获新消息
- 🗣️ **上下文记忆** — 每个联系人独立保持对话上下文

## 📁 项目结构

```
watchat-bot/
├── src/
│   ├── bot.py                  # 主入口（CipherTalk API 模式）
│   ├── wechat_bridge.py        # 桌面自动化模式（pyautogui）
│   ├── msg_monitor.py          # 数据库直读模式（sqlcipher3）
│   ├── notification_monitor.py # Windows 通知监听模式
│   ├── llm.py                  # LLM 调用封装 + 人格系统
│   ├── preprocess.py           # 聊天记录预处理（风格分析）
│   ├── deep_analyze.py         # 深度风格分析
│   ├── decrypt_db.py           # 微信4.x 数据库解密导出
│   ├── diagnose.py             # 微信窗口自动化诊断
│   └── quick_test.py           # 快速功能测试
├── tests/
│   ├── test_send.py              # 发送功能测试
│   ├── test_wcf.py               # WeChatFerry 兼容性测试
│   └── test_wx4py.py             # wx4py 兼容性测试
├── config.example.yaml           # 配置文件模板
├── requirements.txt            # Python 依赖
├── 启动机器人.bat               # Windows 一键启动脚本
├── LICENSE                     # MIT 协议
└── README.md
```

## 🚀 快速开始

### 环境要求

- Windows 10/11（微信桌面版仅支持 Windows/macOS）
- Python 3.10+
- 微信 PC 版 4.x

### 1. 克隆项目

```bash
git clone https://github.com/your-username/watchat-bot.git
cd watchat-bot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 编辑 config.yaml，填入你的：
#   - DeepSeek API Key（或其他 OpenAI 兼容 API）
#   - 个人信息（用于 AI 人格）
#   - 微信数据库路径（可选，如需数据库模式）
```

### 4. 选择运行模式

#### 模式 A：CipherTalk API（推荐）

需要先安装并启动 [CipherTalk](https://ciphersaw.com)，它会暴露本地 API：

```bash
python src/bot.py
```

#### 模式 B：桌面自动化

无需额外工具，直接操控微信窗口：

```bash
python src/wechat_bridge.py
```

启动后选择：
- `1` — 扫描回复所有未读联系人
- `2` — 只监听指定联系人
- `3` — 命令行手动测试

#### 模式 C：数据库直读

从加密数据库直接读取消息（无需微信前台运行）：

```bash
# 先确保 config.yaml 中配置了 db_key 和 source_db
python src/msg_monitor.py
```

> ⚠️ 需要先用解密工具获取微信数据库解密密钥。

## 🔧 配置说明

`config.yaml` 主要配置项：

| 配置项 | 说明 |
|--------|------|
| `llm.api_key` | DeepSeek / OpenAI API Key |
| `llm.model` | 模型名称，默认 `deepseek-chat` |
| `llm.base_url` | API 地址 |
| `wechat.whitelist` | 回复白名单（留空回复所有人） |
| `wechat.min_interval` / `max_interval` | 消息间隔（秒） |
| `persona` | 个人设定（机器人回复的依据） |
| `data.records_dir` | 聊天记录存放路径 |
| `data.source_db` | 解密后的微信数据库路径（可选） |
| `db_key` | 微信数据库解密密钥（可选） |

## 🎭 人格系统

项目通过分析你的真实聊天记录来模仿你的说话风格：

```bash
# Step 1: 从微信数据库导出聊天记录
python src/decrypt_db.py

# Step 2: 分析说话风格，生成风格文件
python src/preprocess.py

# Step 3: (可选) 深度分析
python src/deep_analyze.py
```

分析结果保存在 `data/chat_records/` 目录下，LLM 模块会自动加载 `style_profile.txt` 作为系统提示词的一部分。

## ⚠️ 注意事项

- **仅供学习和个人使用**，请勿用于骚扰、垃圾消息等用途
- 微信官方禁止使用外挂/自动化工具，使用风险自负
- 建议设置较长的消息间隔（5-15秒），避免触发微信的风控
- 不要将包含真实 API Key 和个人信息的 `config.yaml` 上传到公开仓库

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)
