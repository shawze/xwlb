import google.generativeai as genai
from typing import List, Dict

# 从 src 包的 config 模块导入全局配置实例
from src.config import global_config
from src.prompt_template import ANALYSIS_PROMPT

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

    prompt = ANALYSIS_PROMPT.format(formatted_news=formatted_news)


    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini分析失败: {e}")
        return f"**AI分析失败**\n原因: {e}"
