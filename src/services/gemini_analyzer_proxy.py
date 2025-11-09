from typing import List, Dict
import requests
import json
from src.config import global_config
from src.prompt_template import ANALYSIS_PROMPT


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

    prompt = ANALYSIS_PROMPT.format(formatted_news=formatted_news)

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

        #print("--- 收到响应 (原始 JSON) ---")
        #print(json.dumps(response_data, indent=2, ensure_ascii=False))

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


# if __name__ == '__main__':
#     analyze_news_with_gemini(["",""])