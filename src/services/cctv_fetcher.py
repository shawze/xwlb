import httpx
import random
import datetime
import logging
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from httpx import ConnectTimeout, ReadTimeout, RemoteProtocolError
import re
from typing import Dict, Any
from bs4 import BeautifulSoup
import pprint
from markdownify import markdownify as md

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 设置 httpx 日志级别为 WARNING，以减少不必要的日志输出
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- 常量定义 ---
CCTV_INDEX_URL = "https://tv.cctv.com/lm/xwlb/index.shtml"
REQUEST_TIMEOUT = httpx.Timeout(60.0, connect=60.0, read=60.0, write=60.0)

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1462.54",
    "ANDROID-com.xunlei.downloadprovider/7.41.0.7945 netWorkType/WIFI appid/40 deviceName/Huawei_Lio-an00 deviceModel/LIO-AN00 OSVersion/7.1.2 protocolVersion/301 platformVersion/10 SDKVersion/220000 Oauth2Client/0.9 (Linux 3_18_48) (JAVA 0) Edg/112.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58"
]

# 正则表达式常量
DATE_PATTERN = re.compile(r"(\d{8})")
CONTENT_PATTERN = re.compile(r"主要内容(.*?)(?:编辑：|$)", re.DOTALL)

# 清理文本常量
TEXT_TO_REMOVE = '**央视网消息**（新闻联播）：'
TITLE_TO_REMOVE = '[视频]'


def _get_headers() -> Dict[str, str]:
    """创建并返回带有随机 User-Agent 的请求头。"""
    return {
        'Cache-Control': 'max-age=0',
        'Cookie': 'language=cn_CN; watch_times=1;',
        'accept-language': 'zh-CN,zh;q=0.9',
        'User-Agent': random.choice(UA_LIST),
    }


def _parse_date_from_title(title: str) -> str:
    """
    从标题中解析新闻日期。

    Args:
        title: 新闻标题。

    Returns:
        格式为 'YYYY-M-D' 的日期字符串。
    """
    match = DATE_PATTERN.search(title)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
            return f"{date_obj.year}-{date_obj.month}-{date_obj.day}"
        except ValueError:
            logging.debug("日期字符串格式无效，将使用当前日期。")
    
    logging.debug("无法从标题中解析出日期，将使用当前日期。")
    return datetime.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout))
)
def fetch_news_data(url: str = CCTV_INDEX_URL) -> Dict[str, Any] | None:
    """
    从新闻联播索引页抓取新闻列表和日期。

    Args:
        url: 索引页 URL。

    Returns:
        包含新闻日期、链接、详细信息和图片 URL 的字典，或在失败时返回 None。
    """
    try:
        headers = _get_headers()
        with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url)
            resp.raise_for_status()
            # resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, 'lxml')
        content_list = soup.find('ul', id='content')
        if not content_list:
            logging.debug("在页面中找不到 id='content' 的列表。")
            return None

        news_data_list = []
        list_items = content_list.find_all('li')

        for item in list_items:
            image_tag = item.find('img')
            image_url = f"https:{image_tag['src']}" if image_tag and 'src' in image_tag.attrs else 'N/A'
            title_link = item.find('a', target='_blank', href=True)

            if title_link:
                news_data_list.append({
                    "title": title_link['title'],
                    "news_links": title_link['href'],
                    "img_urls": image_url
                })
        
        if not news_data_list:
            logging.debug("未找到任何新闻条目。")
            return None

        news_date = _parse_date_from_title(news_data_list[0]['title'])
        
        news_items = news_data_list[1:]

        res = {
            "news_date": news_date,
            "news_links": [item.get("news_links", "") for item in news_items],
            "news_list_detail": [
                {
                    "url": item.get("news_links", ""),
                    "title": item.get("title", "")
                } for item in news_items
            ],
            "img_urls": [item.get("img_urls", "") for item in news_items]
        }
        logging.debug(f"新闻日期: {news_date} ; 共抓取到 {len(res.get('news_links'))} 条新闻, 共{len(res.get('img_urls'))}图片链接")
        print(f"新闻日期: {news_date} ; 共抓取到 {len(res.get('news_links'))} 条新闻, 共{len(res.get('img_urls'))}图片链接")

        return res

    except Exception as e:
        logging.error(f"抓取新闻数据时发生错误: {e}", exc_info=True)
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout, RemoteProtocolError))
)
def fetch_item_content(news_item: Dict[str, str]) -> Dict[str, str] | None:
    """
    获取单个新闻条目的详细内容。

    Args:
        news_item: 包含 'url' 和 'title' 的字典。

    Returns:
        包含清理后的标题和内容的字典，或在失败时返回 None。
    """
    url = news_item.get("url")
    title = news_item.get("title")
    if not url or not title:
        return None

    try:
        headers = _get_headers()
        with httpx.Client(headers=headers, timeout=REQUEST_TIMEOUT) as client:
            response = client.get(url)
            response.raise_for_status()
            # response.encoding = response.apparent_encoding

        if response.text:
            match = CONTENT_PATTERN.search(response.text)
            if match:
                html_doc = match.group(1).strip()
                markdown_text = md(html_doc, heading_style="ATX")
                
                cleaned_text = markdown_text.replace(TEXT_TO_REMOVE, '', 1)
                cleaned_title = title.replace(TITLE_TO_REMOVE, '', 1)
                
                res = {
                    "title": cleaned_title,
                    "content": cleaned_text
                }
                logging.debug(f"抓取新闻: {res.get('title')}, 共{len(res.get('content'))}个文字")
                print(f"抓取新闻: {res.get('title')}, 共{len(res.get('content'))}个文字")

                return res

    except Exception as e:
        logging.error(f"抓取新闻内容时发生错误 (URL: {url}): {e}", exc_info=True)
    
    return None


if __name__ == '__main__':
    data = fetch_news_data()
    if data and "news_list_detail" in data:
        for item in data["news_list_detail"][:2]:
            content = fetch_item_content(item)
            if content:
                # logging.info(pprint.pformat(content))
                pass
