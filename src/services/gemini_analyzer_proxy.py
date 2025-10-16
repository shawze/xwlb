from typing import List, Dict
import requests
import json
from src.config import global_config


# ==========================================================
# 1. 设置你的 API 密钥和模型
# ==========================================================
def analyze_news_with_gemini(news_data: List[Dict[str, str]]) -> str:
    """
    使用 Gemini AI 分析新闻内容列表，并根据预设的模板生成分析报告。

    :param news_data: 包含新闻字典的列表，每个字典含 'title' 和 'content'。
    :return: AI生成的Markdown格式分析报告。
    """

    # 初始化 Gemini API
    # 替换为你在 AI Studio 获取的 API 密钥
    API_KEY = global_config.get("gemini", "api_key")


    # 你要使用的模型
    # 'gemini-pro' 适用于纯文本
    MODEL_NAME = 'gemini-2.5-pro'

    # 这是官方 REST API 的 V1 版端点 (Endpoint)
    # API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL_NAME}:generateContent"
    API_URL = f"https://gemini.228229.xyz/v1/models/{MODEL_NAME}:generateContent"

    # ==========================================================
    # 2. 准备请求
    # ==========================================================

    # 你的提示词

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

    # (关键) 构造请求体 (Payload)
    # 官方 API 要求一个特定的 JSON 结构
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
        # 你还可以在这里添加 "generationConfig" 和 "safetySettings"
        # "generationConfig": {
        #     "temperature": 0.9,
        #     "maxOutputTokens": 1000
        # }
    }

    # (关键) 构造请求头
    # 必须指定 'Content-Type' 为 'application/json'
    headers = {
        'Content-Type': 'application/json'
    }

    # (关键) 构造查询参数
    # API 密钥是通过 URL 的 'key' 参数传递的
    params = {
        'key': API_KEY
    }

    print(f"--- 正在向 {API_URL} 发送 POST 请求 ---")
    # print(f"请求体 (Body): \n{json.dumps(payload, indent=2, ensure_ascii=False)}\n")

    # ==========================================================
    # 3. 发送请求并分析响应
    # ==========================================================

    try:
        # 发送 POST 请求
        response = requests.post(
            API_URL,
            headers=headers,
            params=params,  # API Key 在这里
            json=payload  # 你的提示词在这里
        )

        # 检查 HTTP 状态码
        response.raise_for_status()  # 如果状态码不是 200-299，会引发异常

        # 将响应解析为 JSON
        response_data = response.json()

        print("--- 收到响应 (原始 JSON) ---")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        # ==========================================================
        # 4. 从响应中提取数据
        # ==========================================================

        # 按照 API 返回的结构来提取文本
        # 路径是: candidates[0] -> content -> parts[0] -> text
        try:
            text_content = response_data['candidates'][0]['content']['parts'][0]['text']
            print("\n--- 提取到的回答 ---")
            print(text_content)

            return text_content

        except (KeyError, IndexError) as e:
            print(f"\n错误：无法从响应中解析出文本。错误: {e}")
            print("可能是因为安全设置阻止了回答，请检查 'promptFeedback' 字段。")
            if 'promptFeedback' in response_data:
                print(f"安全反馈: {response_data['promptFeedback']}")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求发生错误: {req_err}")
    except Exception as e:
        print(f"发生未知错误: {e}")


if __name__ == '__main__':
    analyze_news_with_gemini(["",""])