import requests
import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.info, format='%(asctime)s - %(levelname)s - %(message)s')

class XueqiuPublisher:
    """
    用于发布文章到雪球的类。
    """
    # --- API URL常量 ---
    SAVE_DRAFT_URL = "https://mp.xueqiu.com/xq/statuses/draft/save.json"
    TEXT_CHECK_URL = "https://mp.xueqiu.com/xq/statuses/text_check.json"
    SESSION_TOKEN_URL = "https://mp.xueqiu.com/xq/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
    PUBLISH_URL = "https://mp.xueqiu.com/xq/statuses/update.json"
    XUEQIU_COOKIE = 'cookiesu=771761390158192; device_id=aebc7e1ff91d7ce8d048a5687febc015; s=ad17wfnolw; xq_a_token=2e2a47861a21eed7de84f2f191527f89b66b800b; xqat=2e2a47861a21eed7de84f2f191527f89b66b800b; xq_r_token=2d6ee2312ea6097d13a725cbc9fea7b46efcbb59; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjE0ODk0MzA0MTQsImlzcyI6InVjIiwiZXhwIjoxNzYzOTgyNDIzLCJjdG0iOjE3NjEzOTA0MjM2OTgsImNpZCI6ImQ5ZDBuNEFadXAifQ.ekQTQiFM3RFYOuS84FQi-1kiyJxSq9jdVJD1glWe8tV8HbbeXUfPPfNqSvnnUVr8oS1Bc05OYDSoIvrRodABsnA6HtrBbkC3QzFq4CMW055ErCb8UGfF8VoNI0mWtdHBXMKXSOTqjMvJLNiFWJwhmmt_NLpHpR1zxYevzD11cBG8k1qt0fe3ClQizM78O0TRKZhHIZv96uKttVEJsj3xdBaiOSE_qIebgSzLBqq9ZeaJrqZW0zCSHQR3KJp-OcTxHAVIjQKpSD_xW2Jb-3Sd_vM0qlX-55ArLOPgMylJAkgjb-qs9XnIvvitg9F0aEQy8-7CYUf96u3C_mHyK9Ml2g; xq_is_login=1; u=1489430414; acw_tc=3ccdc15117613904376776835e1b1a5964c4cb1a00ef75b0691c917c78e8df; ssxmod_itna=1-eqjxgDyQKGqTD7Dh6AD2GQDOQdAQDXDUuu47t=GcD8xiKDHDIg1YFqCDhA9D4GIFDfhxmxBGGD5D/KeeeDZDG93Dqx0oiLlre5xei49CDuFYQ7jOQ43sBwgFK3VK5_RSEwVYYuGfOH0tp_D4i8xeDU4GnD067QmxiDYYLDBYD74G_DDeDixGmFeDSlDD9DGP=x1WbgeDEDYP=xA3Di4D_nmbDmT4DGdfex7QTSe4D0q_mh0DDeRvx_c9eccwGq=Kk57D=x0tTDBLG/K4=MPC2hDak2FMHa_bDzqzDtwWNb12GsETadZc41TdlxYYWdGnzf2D7GxlxeWuDk2D_YbYie5YiFG8_AxQmrYm5xxD8_GmmiNwDGYznuzBTsGDb4roNdG4RD32ohxooTxPnog752BQ8dYY0rGYYK0De05YiY1jGKiDD; ssxmod_itna2=1-eqjxgDyQKGqTD7Dh6AD2GQDOQdAQDXDUuu47t=GcD8xiKDHDIg1YFqCDhA9D4GIFDfhxmxBGGDeGIDxxWuvi1SWYt1lKm=Y_76m4cdexD'  # <--- 在这里填入您的 COOKIE


    def __init__(self,cookie:str, title: str, content: str):
        """
        初始化 XueqiuPublisher。

        Args:
            cookie (str): 雪球用户登录后的 cookie。
            title (str): 文章标题。
            content (str): 文章内容 (HTML 或 Markdown)。
        """
        if not cookie:
            raise ValueError("Cookie 不能为空")
        # cookie = self.XUEQIU_COOKIE
        # logging.warning("请在 if __name__ == '__main__': 代码块中设置 XUEQIU_COOKIE 变量。")

        self.title = title
        self.content = content
        self.session = requests.Session()
        self.draft_id = None
        self.session_token = None

        # 设置通用的请求头
        self.base_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "DNT": "1",
            "Host": "mp.xueqiu.com",
            "Origin": "https://mp.xueqiu.com",
            "Referer": "https://mp.xueqiu.com/writeV2/?position=pc_creator_post",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
            "Cookie": cookie
        }
        self.post_headers = self.base_headers.copy()
        self.post_headers["Content-Type"] = "application/x-www-form-urlencoded"

    def _save_draft(self) -> bool:
        """第一步：保存草稿并获取 draft_id。"""
        payload = {
            "id": "",
            "text": self.content, # 注意：雪球的 text 字段对应文章内容
            "title": self.title,   # title 字段对应文章标题
            "cover_pic": "",
            "flags": "false",
            "original_event": "",
            "legal_user_visible": "false",
            "is_private": "false",
        }
        try:
            response = self.session.post(self.SAVE_DRAFT_URL, headers=self.post_headers, data=payload)
            response.raise_for_status()
            data = response.json()
            self.draft_id = data.get("id")
            if self.draft_id:
                logging.debug(f"保存草稿成功，Draft ID: {self.draft_id}")
                return True
            logging.error(f"保存草稿失败: {data}")
            return False
        except requests.RequestException as e:
            logging.error(f"保存草稿时发生网络错误: {e}")
            return False

    def _check_text(self) -> bool:
        """第二步：对草稿内容进行检查。"""
        payload = {
            "text": self.content,
            "title": self.title,
            "type": "0",
        }
        try:
            response = self.session.post(self.TEXT_CHECK_URL, headers=self.post_headers, data=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("success") is True:
                logging.debug("文本内容检查通过。")
                return True
            logging.error(f"文本内容检查失败: {data}")
            return False
        except requests.RequestException as e:
            logging.error(f"文本检查时发生网络错误: {e}")
            return False

    def _get_session_token(self) -> bool:
        """第三步：获取用于发布的 session_token。"""
        try:
            response = self.session.get(self.SESSION_TOKEN_URL, headers=self.base_headers)
            response.raise_for_status()
            data = response.json()
            self.session_token = data.get("session_token")
            if self.session_token:
                logging.debug(f"获取 Session Token 成功: {self.session_token}")
                return True
            logging.error(f"获取 Session Token 失败: {data}")
            return False
        except requests.RequestException as e:
            logging.error(f"获取 Session Token 时发生网络错误: {e}")
            return False

    def _publish_post(self):
        """第四步：使用 draft_id 和 session_token 发布文章。"""
        payload = {
            "title": self.title,
            "status": self.content,
            "cover_pic": "",
            "show_cover_pic": "false",
            "original": "false",
            "industry_category_name": "",
            "original_event_id": "",
            "original_event_active": "true",
            "legal_user_visible": "false",
            "is_private": "false",
            "legal_user_state": "open",
            "post_position": "pc_creator_post",
            "draft_id": self.draft_id,
            "allow_reward": "false",
            "session_token": self.session_token,
        }
        try:
            response = self.session.post(self.PUBLISH_URL, headers=self.post_headers, data=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("error_code"):
                logging.error(f"发布失败: {data.get('error_description')}")
            else:
                post_id = data.get("id")
                logging.debug(f"文章发布成功！Post ID: {post_id}")
        except requests.RequestException as e:
            logging.error(f"发布文章时发生网络错误: {e}")

    def publish(self):
        """执行完整的发布流程。"""
        if self._save_draft() and self._check_text() and self._get_session_token():
            self._publish_post()
        else:
            logging.error("发布流程中止，请检查之前的错误信息。")


if __name__ == '__main__':
    # 请在这里填入您自己的 Cookie
    # # 如何获取 Cookie:
    # 1. 登录雪球 (xueqiu.com)
    # 2. 打开浏览器开发者工具 (F12)
    # 3. 切换到“网络”(Network) 标签页
    # 4. 刷新页面，找到任意一个对 mp.xueqiu.com 的请求
    # 5. 在请求头中找到 "Cookie" 并复制其值

    # --- 要发布的文章内容 ---
    post_title = "这是一个测试标题"
    post_content = "这是文章的**内容**部分。支持 Markdown 格式。"

    # --- 执行发布 ---
    publisher = XueqiuPublisher(title=post_title,
                                content=post_content)
    publisher.publish()
