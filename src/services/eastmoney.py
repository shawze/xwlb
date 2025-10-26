import json
import logging
from urllib.parse import quote
import requests
from src.config import global_config


# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



class EastmoneyPublisher:
    """用于发布文章到东方财富的类。"""
    
    API_URL = "https://emstockdiag.eastmoney.com/apistock/Tran/GetData?platform="

    def __init__(self,
                 ctoken: str, utoken: str,
                 title: str, content: str):
        """
        初始化 EastmoneyPublisher。

        Args:
            ctoken (str): 东方财富 ctoken.
            utoken (str): 东方财富 utoken.
            title (str): 文章标题.
            content (str): 文章内容 (HTML format).
        """
        if not ctoken or not utoken:
            raise ValueError("ctoken 和 utoken 不能为空。")
        
        self.ctoken = ctoken
        self.utoken = utoken
        self.title = title
        self.content = content

    def _prepare_payload(self) -> dict:
        """准备要发送的 payload。"""
        parm = [
            {'location': 'WEB|CFH|usercenter|FALSE'},
            {'title': self.title},
            {'text': f'<div class="xeditor_content cfh_web">{self.content}</div>'},
            {'columns': '2'},
            {'cover': ''},
            {'issimplevideo': '0'},
            {'videos': ''},
            {'vods': ''},
            {'isoriginal': '0'},
            {'cfh_ttjj': ''},
            {'tipstate': '1'},
            {'spcolumns': ''},
            {'jjzh_type': ''},
            {'jjzh_code': ''},
            {'textsource': '0'},
            {'replyauthority': '0'},
            {'ip': '$IP$'},
            {'deviceid': '100'},
            {'version': '100'},
            {'plat': 'web'},
            {'product': 'CFH'},
            {'ctoken': self.ctoken},
            {'utoken': self.utoken}
        ]

        parm_with_encoded_values = [{key: quote(value) for key, value in item.items()} for item in parm]
        parm_as_text = json.dumps(parm_with_encoded_values, ensure_ascii=False, separators=(',', ':'))

        return {
            "pageUrl": "https://mp.eastmoney.com/collect/pc_article/index.html#/",
            "parm": parm_as_text,
            "path": "postopt/api/post/PublishArticleWeb",
        }

    def publish(self):
        """执行发布流程。"""
        payload = self._prepare_payload()
        
        try:
            response = requests.post(url=self.API_URL, data=payload)
            response.raise_for_status()
            res = response.json()

            if str(res.get("RCode")) == "200":
                r_data_str = res.get("RData", "{}")
                r_data = json.loads(r_data_str)
                error_code = r_data.get("error_code")
                res_msg = r_data.get("me")
                if error_code:
                    logging.error(f"东方财富发布失败，错误码：{error_code}，返回信息: {res_msg}")
                else:
                    logging.debug(f"东方财富发布成功，返回信息: {res_msg}")
                    return True
            else:
                logging.error(f"东方财富发布请求失败: {res}")

        except requests.RequestException as e:
            logging.error(f"发布到东方财富时发生网络错误: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"解析东方财富返回的 JSON 时出错: {e}")

if __name__ == '__main__':
    # --- 使用示例 ---
    # 在实际使用中，这些值应从安全的配置文件中加载

    TEST_CTOKEN = global_config.get('Eastmoney', 'ctoken')
    TEST_UTOKEN = global_config.get('Eastmoney', 'utoken')

    # TEST_CTOKEN = "your_ctoken_here"
    # TEST_UTOKEN = "your_utoken_here"
    TEST_TITLE = "这是一个测试标题"
    TEST_CONTENT = "<p>这是文章的 <b>HTML</b> 内容。</p>"

    if TEST_CTOKEN == "your_ctoken_here":
        logging.warning("请在 if __name__ == '__main__': 代码块中设置真实的 ctoken 和 utoken 进行测试。")
    else:
        publisher = EastmoneyPublisher(
            ctoken=TEST_CTOKEN,
            utoken=TEST_UTOKEN,
            title=TEST_TITLE,
            content=TEST_CONTENT
        )
        publisher.publish()
