import httpx
import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from httpx import ConnectTimeout, ReadTimeout, RemoteProtocolError
import re # 导入re模块
from typing import List, Dict, Any, Optional

# --- 配置项 ---
CRAWL_SERVICE_URL = "http://228229.xyz:11235/crawl"
CCTV_INDEX_URL = "https://tv.cctv.com/lm/xwlb/index.shtml"
REQUEST_TIMEOUT = httpx.Timeout(60.0, connect=60.0, read=60.0, write=60.0)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout))
)
def get_date_formats(dt_obj: datetime.datetime) -> List[str]:
    """Generates two date string formats: YYYY/MM/DD and YYYY/M/D."""
    format1 = dt_obj.strftime("%Y/%m/%d")
    format2 = f"{dt_obj.year}/{dt_obj.month}/{dt_obj.day}"
    return [format1, format2]

async def fetch_news_data() -> Optional[Dict[str, Any]]:
    """从远程服务抓取新闻链接、图片链接和新闻日期，并以字典形式返回。"""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(CRAWL_SERVICE_URL, json={"urls": [CCTV_INDEX_URL]})
            response.raise_for_status()
            data = response.json().get("results")[0]

            # 提取新闻链接
            news_links_raw = data.get("links", {}).get("internal", [])
            news_links = [{
                "title": item.get("title"),
                "href": item.get("href"),
            } for item in news_links_raw if "视频" in item.get("title", "")]

            if not news_links:
                print("未能获取到任何新闻链接。")
                return None

            # 从第一个链接中解析新闻日期
            news_date = None
            first_link = news_links[0]['href']
            match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', first_link)
            if match:
                year, month, day = match.groups()
                news_date = f"{year}-{month}-{day}"
                print(f"解析出的新闻日期为: {news_date}")
            else:
                print("无法从链接中解析出日期，将使用当前日期。")
                news_date = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


            # 提取图片链接
            news_date_formats = datetime.datetime.strptime(news_date, "%Y-%m-%d")
            news_date_formats = get_date_formats(news_date_formats)

            img_list_all = data.get("media", {}).get("images", [])
            img_urls = []
            for item in img_list_all:
                src = item.get("src")
                if src:
                    # 检查图片URL中是否包含任意一种日期格式
                    if any(date_fmt in src for date_fmt in news_date_formats):
                        img_urls.append("https:" + src)
            
            print(f"抓取到 {len(news_links)} 条新闻链接和 {len(img_urls)} 个图片链接。")
            
            return {
                "news_date": news_date,
                "news_links": news_links,
                "img_urls": img_urls
            }
        except Exception as e:
            print(f"抓取新闻数据时发生错误: {e}")
            return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout, RemoteProtocolError))
)
async def fetch_item_content(url: str):
    """抓取单条新闻的详细内容。"""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(CRAWL_SERVICE_URL, json={"urls": [url]})
        response.raise_for_status()
        res = response.json().get("results")[0]
        if res.get("success"):
            res_markdown = res.get("markdown", {}).get("raw_markdown", "")
            # 使用更健壮的正则，即使找不到“编辑：”也能继续
            match = re.search(r"主要内容(.*?)(?:编辑：|$)", res_markdown, re.DOTALL)
            if match:
                return {
                    "title": res.get("metadata", {}).get("title", "无标题"),
                    "content": match.group(1).strip()
                }
    return None
