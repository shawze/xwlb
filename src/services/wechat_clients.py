import requests
import json
import datetime
import re # 用于企业微信的_media_upload方法
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 从 src 包的 config 模块导入全局配置实例
from src.config import global_config
from src.utils.logger import logger # 导入日志模块

import logging
logging.basicConfig(level=logging.info, format='%(asctime)s - %(levelname)s - %(message)s')



class WeChatMPClient:
    """
    一个用于与微信公众号API交互的客户端类。
    封装了获取access_token、上传素材、创建和发布草稿等常用功能。
    """
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self):
        appid = global_config.get("wechat_mp", "appid")
        secret = global_config.get("wechat_mp", "appsecret")
        self.session = requests.Session()
        self._refresh_access_token(appid, secret)

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def _refresh_access_token(self, appid: str, secret: str):
        """获取或刷新 access_token。"""
        url = f"{self.BASE_URL}/token"
        params = {'grant_type': 'client_credential', 'appid': appid, 'secret': secret}
        try:
            response = self.session.get(url, params=params)
            data = self._handle_response(response)
            self.session.params['access_token'] = data['access_token']
            logger.debug("公众号 access_token 获取成功。")
        except Exception as e:
            logger.error(f"公众号 access_token 获取失败: {e}")
            raise

    def _handle_response(self, response):
        """统一处理API响应。"""
        try:
            response.raise_for_status()
            data = response.json()
            if data.get('errcode', 0) != 0:
                error_msg = f"[公众号API错误] {data.get('errmsg', '未知错误')} (errcode: {data.get('errcode')})"
                logger.error(error_msg)
                raise ValueError(error_msg)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"公众号API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"公众号API响应JSON解析失败: {e}, 响应内容: {response.text}")
            raise
    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def upload_image(self, image_file_path: str) -> str:
        """上传永久图片素材。"""
        url = f"{self.BASE_URL}/material/add_material"
        try:
            with open(image_file_path, 'rb') as file:
                files = {'media': file}
                params = {'type': 'image'}
                response = self.session.post(url, params=params, files=files)
            data = self._handle_response(response)
            logger.debug(f"公众号图片上传成功: {json.dumps(data, ensure_ascii=False, indent=2)}")
            return data['media_id']
        except Exception as e:
            logger.error(f"公众号图片上传失败: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def create_draft(self, title: str, content: str, thumb_media_id: str, **kwargs) -> str:
        """创建草稿。"""
        url = f"{self.BASE_URL}/draft/add"

        draft_data = {
            "articles" : [{
                "title": title,
                "thumb_media_id": thumb_media_id,
                "content": content,
                "author": kwargs.get("author", "xiaoze"),
                "digest": kwargs.get("digest", "新闻联播 解读 股票 政策 财经"),
                "show_cover_pic": 1 if thumb_media_id else 0
                # "content_source_url": kwargs.get("content_source_url", "https://tv.cctv.com/lm/xwlb/")
            }]
        }
        try:
            # 此段代码是处理中文编码,请务删除
            payload = json.dumps(draft_data, ensure_ascii=False).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            response = self.session.post(url, data=payload, headers=headers)

            data = self._handle_response(response)
            logger.debug(f"公众号草稿创建成功: {json.dumps(data, ensure_ascii=False, indent=2)}")
            return data['media_id']
        except Exception as e:
            logger.error(f"公众号草稿创建失败: {e}")
            raise


class WeChatWorkClient:
    """
    企业微信机器人消息发送客户端。
    """
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self):
        self._id = global_config.get('work_wx', 'id')
        self._secret = global_config.get('work_wx', 'secret')
        self._agentid = global_config.get('work_wx', 'agentid')
        self.touser = global_config.get('work_wx', 'touser', strip_quote=False) # Keep quotes for @all
        self.session = requests.Session()
        self._refresh_access_token()

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def _refresh_access_token(self):
        """获取或刷新 access_token。"""
        url = f"{self.BASE_URL}/gettoken"
        params = {'corpid': self._id, 'corpsecret': self._secret}
        try:
            # 增加超时时间，例如10秒
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('errcode', 0) != 0:
                error_msg = f"[企业微信API错误] {data.get('errmsg', '未知错误')}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            self.session.params['access_token'] = data['access_token']
            logger.debug("企业微信 access_token 获取成功。")
        except requests.exceptions.RequestException as e:
            logger.error(f"企业微信 access_token 获取失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"企业微信 access_token 响应JSON解析失败: {e}, 响应内容: {response.text}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def _media_upload(self, image_path: str, media_type: str = 'image') -> str:
        """上传文件到企业微信临时文件。"""
        url = f"{self.BASE_URL}/media/upload"
        try:
            with open(image_path, 'rb') as f:
                files = {'media': (image_path, f, f'{media_type}/jpeg')}
                response = self.session.post(url, params={'type': media_type}, files=files)
            response.raise_for_status()
            data = response.json()
            if data.get('errcode', 0) != 0:
                error_msg = f"[企业微信媒体上传错误] {data.get('errmsg', '未知错误')}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.debug(f"企业微信媒体上传成功，media_id: {data['media_id']}")
            return data['media_id']
        except Exception as e:
            logger.error(f"企业微信媒体上传失败: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def upload_temp_image(self, image_file_path: str) -> str:
        """上传临时图片素材，用于图文消息的封面。"""
        return self._media_upload(image_file_path, media_type='image')

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避等待策略
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # 仅在网络连接等错误时重试
        reraise=True  # 重试失败后，重新抛出最后的异常
    )
    def send_mpnews(self, title: str, content: str, thumb_media_id: str, **kwargs):
        """发送图文消息。"""
        url = f"{self.BASE_URL}/message/send"
        payload = {
            "touser": self.touser,
            "msgtype": "mpnews",
            "agentid": self._agentid,
            "mpnews": {"articles": [{
                "title": title,
                "thumb_media_id": thumb_media_id,
                "content": content,
                "content_source_url": kwargs.get("content_source_url", ""),
                "digest": kwargs.get("digest", "AI分析报告")
            }]},
            "safe": 0
        }
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('errcode', 0) != 0:
                error_msg = f"[企业微信发送错误] {data.get('errmsg', '未知错误')}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.debug("企业微信图文消息发送成功。")
        except Exception as e:
            logger.error(f"企业微信图文消息发送失败: {e}")
            raise