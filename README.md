# CCTV News (新闻联播) AI Assistant

## 1. 项目概述

本项目是一个全自动化的新闻处理与发布工作流。它会自动抓取每日的央视《新闻联播》文字稿，利用 Google Gemini Pro 模型进行深度分析、总结和解读，生成适合移动端阅读的文章，并自动发布到企业微信和微信公众号平台。

项目核心设计为**分阶段、可恢复的自动化流程**。整个工作流无需人工干预，并内置强大的缓存机制，能自动从上次失败或中断的步骤继续执行，旨在高效、稳定地将权威新闻转化为易于传播和理解的AI洞察。

## 2. 主要功能

*   **分阶段可恢复工作流**: 将核心任务拆分为**加载、获取、分析、封面、发布**五个阶段。系统会自动检测每个阶段的产物是否存在，从而实现断点续传，极大提升了稳定性。
*   **智能AI分析**: 集成 Google Gemini Pro (`gemini-2.5-pro`)，基于优化的专业提示词（Prompt），对新闻内容进行高质量的摘要、亮点提炼和多维影响评估。
*   **多平台发布**: 支持一键发布到**企业微信**应用和**微信公众号**（作为草稿）。
*   **智能化缓存**: 内置强大的缓存机制，不仅缓存新闻内容和AI分析结果，还包括封面图片的`Media ID`和发布状态。缓存有严格的**时效性检查**，确保总是在正确的时间获取新数据，避免重复工作。
*   **智能封面生成**: 自动抓取当天新闻图片，并从中选取6张，智能拼接成一张`3x2`的网格封面图，比单图封面更具信息量。若图片不足，则使用默认封面。
*   **高度可配置**: 所有API密钥、发布目标以及调试开关，都可通过`config/config.ini`文件进行灵活配置，无需修改代码。
*   **强大的调试模式**: 提供一系列`force_*`开关，可在调试时强制执行特定步骤（如强制重新获取数据、强制重新分析、强制发布等），极大地方便了开发和测试。

## 3. 项目结构

```
.
├── config/
│   └── config.example.ini  # 配置文件模板，需复制为 config.ini
├── images/
│   ├── collages/           # 自动生成的封面拼接图存放于此
│   └── default_cover.png   # 默认封面图
├── logs/
│   └── app.log             # 运行日志文件
├── src/
│   ├── main.py             # 主程序入口与工作流调度器
│   ├── config.py           # 配置加载模块
│   ├── services/           # 核心服务
│   │   ├── cctv_crawler.py   # 新闻抓取服务
│   │   ├── gemini_analyzer.py# Gemini AI分析服务
│   │   └── wechat_clients.py # 微信客户端服务
│   └── utils/
│       ├── image_processor.py# 封面图生成工具
│       └── logger.py         # 日志记录工具
├── .gitignore
├── requirements.txt        # Python 依赖列表
├── news_data.json          # 核心数据缓存文件（自动生成）
└── README.md               # 本文档
```

## 4. 安装与设置

### 4.1. 环境准备

*   确保您已安装 Python 3.9 或更高版本。

### 4.2. 安装依赖

克隆或下载本项目到本地后，在项目根目录下打开终端，运行以下命令安装所有必需的库：

```bash
pip install -r requirements.txt
```

### 4.3. 配置文件

1.  将 `config/config.example.ini` 文件复制一份，并重命名为 `config.ini`。
2.  打开 `config.ini` 并根据您的实际情况修改。

*   **[gemini]**:
    *   `api_key`: 填入您的 Google Gemini API 密钥。

*   **[wechat_mp]** (微信公众号):
    *   `appid`: 填入您的公众号 AppID。
    *   `appsecret`: 填入您的公众号 AppSecret。

*   **[work_wx]** (企业微信):
    *   `enable`: `True` 或 `False`，控制是否启用企业微信发布。
    *   `id`: 填入您的企业微信 CorpID。
    *   `agentid`: 填入您要使用的企业微信应用的 AgentId。
    *   `secret`: 填入该应用的 Secret。
    *   `touser`: （可选）指定接收消息的成员ID，`@all`表示所有人。

## 5. 使用方法

### 5.1. 运行脚本

直接在项目根目录下运行 `main.py`：

```bash
python src/main.py
```

### 5.2. 工作流详解

脚本遵循一个含五个阶段的自动化工作流。它会检查 `news_data.json` 缓存文件的状态，自动从需要执行的第一步开始。

*   **阶段 1: 数据加载与状态检查**
    *   检查 `news_data.json` 是否存在且有效（根据新闻日期和获取时间判断）。如果缓存有效，则跳过后续的获取和分析阶段。

*   **阶段 2: 内容获取**
    *   **2.1 获取新闻列表**: 如果没有有效缓存，则从CCTV网站抓取当天新闻的标题、链接和图片URL。
    *   **2.2 获取新闻详情**: 如果新闻内容缺失，则并发抓取所有新闻的详细正文。

*   **阶段 3: AI分析**
    *   如果AI分析结果缺失，则调用 Gemini API 对所有新闻内容进行汇总分析。

*   **阶段 4: 封面图生成与上传**
    *   如果封面 `Media ID` 缺失，则执行以下操作：
        1.  下载新闻图片。
        2.  拼接为一张 `3x2` 的网格图。
        3.  分别上传到微信公众号和企业微信，获取 `Media ID` 并存入缓存。

*   **阶段 5: 多平台发布**
    *   检查各平台是否已发布过。如果未发布，则执行发布操作，并记录发布时间戳，防止重复发送。

## 6. 配置详解

`config.ini` 文件中的 `[StageControl]` 和 `[DebugControl]` 部分允许您精细化控制脚本的行为。

### [StageControl] - 发布阶段开关

```ini
[StageControl]
# True: 允许发布到企业微信。
publish_wechat_work = True
# True: 允许发布到微信公众号。
publish_wechat_mp = True
```

### [DebugControl] - 强制执行开关

这些开关用于调试，设置为 `True` 可以强制执行某个步骤，忽略已有的缓存。

```ini
[DebugControl]
# 强制重新获取新闻列表（链接、日期、图片URL）。
force_fetch_news = False

# 强制重新获取每条新闻的详细内容。
force_fetch_contents = False

# 强制重新调用Gemini进行分析。
force_rerun_analysis = False

# 强制重新生成和上传封面，获取新的Media ID。
force_regenerate_cover = False

# 强制发布到企业微信（即使之前已发布过）。
force_publish_work = False

# 强制发布到微信公众号（即使之前已发布过）。
force_publish_mp = False
```

## 7. 缓存机制

*   **缓存文件**: `news_data.json`
*   **缓存内容**: 新闻日期、链接、图片URL、新闻正文、AI分析结果、封面图的Media ID、各平台的发布时间戳等。
*   **缓存策略**: 每次成功运行后，数据都会被完整记录。下次运行时，程序会检查缓存的 `fetch_timestamp`。如果数据是在当天新闻联播之后获取的，则认为缓存有效，直接进入发布阶段，大大提高了效率并节约了API成本。