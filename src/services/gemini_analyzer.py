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
    # 角色
    你是一位顶级的首席证券分析师，你的任务是整合、分析以下所有新闻信息，并为投资者撰写一份清晰、深刻、逻辑严谨的【市场影响分析简报】。

    # 任务要求
    1.  **整合分析**：将所有输入的新闻视为一个整体，分析它们之间的关联、协同或矛盾之处，并综合判断其市场影响，但请简洁输出。
    2.  **格式规范**：严格使用Markdown格式进行组织，格式中避免不必要的“:”或者“：”，直接输出简报内容，不要包含任何格式外的开场白或对话。

    # 新闻输入
    ---
    {formatted_news}
    ---

    # 分析简报框架

    ### **一、市场影响综合研判**
    (综合所有新闻，用一到两句话，精准概括新闻核心内容。)

    ### **二、关键信息与数据提取**
    (列出所有新闻中，支撑你后续分析的关键事实、数据、政策或人物引述)

    ### **三、利好影响分析**
    (对于每只股票，如果新闻中涉及到具体企业请直接列出并分析，清晰阐述其受益的核心逻辑。)

    ### **四、利空影响分析**
    (对于每只股票，如果新闻中涉及到具体企业请直接列出并分析，说明其受损的核心原因。)

    ### **五、潜在风险与不确定性**
    * (指出本次分析中，可能影响判断准确性的最大风险、事件发展的不确定性或需要进一步观察的关键因素。)

    ### **六、免责声明**
    本简报内容基于公开新闻信息分析，仅供参考，不构成任何投资建议。市场有风险，投资需谨慎，投资者应独立判断并自行承担风险。


    """

    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini分析失败: {e}")
        return f"**AI分析失败**\n原因: {e}"
