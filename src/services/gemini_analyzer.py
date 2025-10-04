import google.generativeai as genai
from typing import List, Dict

# 从 src 包的 config 模块导入全局配置实例
from src.config import global_config

# 初始化 Gemini API
genai.configure(api_key=global_config.get("gemini", "api_key"))

async def analyze_news_with_gemini(news_data: List[Dict[str, str]]) -> str:
    """
    使用 Gemini AI 分析新闻内容列表，并根据预设的模板生成分析报告。

    :param news_data: 包含新闻字典的列表，每个字典含 'title' 和 'content'。
    :return: AI生成的Markdown格式分析报告。
    """
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # 将新闻列表格式化为字符串
    formatted_news = "\n".join([f"标题: {item['title']}\n内容: {item['content']}\n---" for item in news_data])

    prompt = f"""
    请扮演一名资深的新闻、财经分析师，遵循以下框架，对提供的新闻联播内容进行专业、审慎的分析，并以Markdown格式输出。请直接回答，不要包含任何格式外的开场白。

    1.  **核心要点摘要 (Executive Summary):**
        * (用不超过三句话，精准概括所有新闻的核心事件及其最重要的影响)

    2.  **关键信息与数据提取 (Key Facts & Data):**
        * (列出所有新闻中，支撑你后续分析的关键事实、数据、政策或人物引述)

    3.  **多维影响评估 (Multi-Level Impact Assessment):**
        * **宏观经济层面:** (分析这些事件对整体经济的潜在传导效应)
        * **中观行业层面:** (指出可能受益和受损的具体板块或投资主题，并阐述逻辑)

    4.  **前景展望与风险提示 (Outlook & Risk Factors):**
        * **未来观察点:** (投资者应密切关注哪些后续信号，以验证或调整你的分析？)
        * **潜在风险:** (你的分析结论是基于哪些核心假设？最大风险是什么？)

    ----
    **【新闻原始内容】**
    {formatted_news}
    """
    
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini分析失败: {e}")
        return f"**AI分析失败**\n原因: {e}"
