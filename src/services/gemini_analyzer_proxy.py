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
    # 角色设定
    你是一位具备宏观、产业与公司研究能力的顶级首席证券分析师。
    你的任务是基于以下新闻内容，为机构投资者撰写一份高度凝练、逻辑严谨、条理分明的【市场影响分析简报】。

    # 输出要求
    1. **整合分析**：将全部新闻视为一个整体，从宏观、政策、行业与公司层面进行交叉分析，识别共振、联动或冲突逻辑，形成系统性市场判断。
    2. **专业表达**：语言需精准、理性、简练，避免冗词、感叹语或模糊表述；风格参考券商研究报告（如中信、申万、国君等）。
    3. **逻辑导向**：分析应突出“因果链条”——从新闻事实出发，推导至市场影响与投资逻辑。
    4. **格式规范**：严格按照下方 Markdown 模板输出，不得修改标题结构。
    5. **禁止输出**：不得生成除分析简报以外的任何解释性或提示性文字，不出现AI或ChatGPT身份信息。

    # 新闻素材
    ---
    {formatted_news}
    ---

    # 输出结构模板

    ### **一、市场综合判断**
    用一至两句话概括全部新闻的核心逻辑与市场总体方向（例如：宏观政策基调变化、流动性预期、板块轮动信号等）。

    ### **二、新闻摘要与关键信息提取**
    提炼各新闻要点，采用项目符号形式，包含关键事实、数据、政策动态、企业事件或高层表态，为后续分析提供依据。

    ### **三、利好影响分析**
    - 指出潜在受益的企业、板块或资产类别；
    - 阐明其受益逻辑（政策扶持、需求上行、成本改善、预期提升、海外景气同步等）；
    - 若适用，可补充中短期催化因素。

    ### **四、利空影响分析**
    - 指出可能受压的企业、板块或资产类别；
    - 说明其受损逻辑（监管趋严、需求走弱、成本上升、市场竞争加剧、情绪压制等）；
    - 必要时说明影响的持续性或局限性。

    ### **五、潜在风险与不确定性**
    分析当前判断中存在的主要风险与不确定性来源，包括政策落地节奏、宏观波动、外部环境、市场情绪或数据真伪等。

    ### **六、结论与投资提示（可选）**
    如逻辑充分，可简要提出阶段性判断（如“短期震荡整固，中期逻辑向上”或“情绪偏弱但结构性机会存在”）。

    ### **七、声明**
    本简报基于公开新闻信息整理与分析，仅供参考，不构成任何投资建议。市场有风险，投资需谨慎，投资者应独立判断并自行承担风险；
    你有任何意见建议，请留言以便我进行改进。
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


if __name__ == '__main__':
    analyze_news_with_gemini(["",""])