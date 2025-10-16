import httpx
import random
import requests
import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from httpx import ConnectTimeout, ReadTimeout, RemoteProtocolError
import re # 导入re模块
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import pprint
from markdownify import markdownify as md

# --- 配置项 ---
CRAWL_SERVICE_URL = "http://228229.xyz:11235/crawl"
CCTV_INDEX_URL = "https://tv.cctv.com/lm/xwlb/index.shtml"
REQUEST_TIMEOUT = httpx.Timeout(60.0, connect=60.0, read=60.0, write=60.0)

ua_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1462.54",
    "ANDROID-com.xunlei.downloadprovider/7.41.0.7945 netWorkType/WIFI appid/40 deviceName/Huawei_Lio-an00 deviceModel/LIO-AN00 OSVersion/7.1.2 protocolVersion/301 platformVersion/10 SDKVersion/220000 Oauth2Client/0.9 (Linux 3_18_48) (JAVA 0) Edg/112.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58"

]
ua = random.choice(ua_list)

headers = {'Cache-Control': 'max-age=0', 'Cookie': 'language=cn_CN; watch_times=1; ',
                   'accept-language': 'zh-CN,zh;q=0.9',
                   'User-Agent': ua,
           }


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout))
)
def fetch_news_data(url=CCTV_INDEX_URL):
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = resp.apparent_encoding
        resp.raise_for_status()
        # 1. 创建 BeautifulSoup 对象，指定 'lxml' 解析器
        soup = BeautifulSoup(resp.text, 'lxml')
        # 2. 创建一个列表来存放结果
        news_data_list = []
        # 3. 查找所有 <li> 标签
        # 通过 id="content" 定位到父节点，再查找所有 <li>
        content_list = soup.find('ul', id='content')
        if content_list:
            list_items = content_list.find_all('li')
            # 4. 遍历每一个 <li> 标签
            for item in list_items:
                # 查找 <img> 标签并获取 src 属性
                image_tag = item.find('img')
                image_url = "https:" + image_tag['src'] if image_tag else 'N/A'
                title_link = item.find('a', target='_blank', href=True)
                if title_link:
                    # 获取 URL
                    url = title_link['href']
                    # 获取 新闻标题
                    title = title_link['title']
                    # 存入字典
                    news_item =  {
                        "title": title,
                        "news_links": url,
                        "img_urls": image_url
                    }
                    news_data_list.append(news_item)
            # # 去除第一条 完整视频
            # news_data = news_data[1:]
            # 5. 打印结果
            # pprint.pprint(news_data_list)

            # 从第一个链接中解析新闻日期
            news_date = None
            first_title = news_data_list[0]['title']
            pattern = r"(\d{8})"
            match = re.search(pattern, first_title)
            if match:

                if match:
                    date_str = match.group(1)
                    try:
                        date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
                        news_date = f"{date_obj.year}-{date_obj.month}-{date_obj.day}"
                    except ValueError:
                        print("字符串不是一个有效的 YYYYMMDD 格式")
                print(f"解析出的新闻日期为: {news_date}")
            else:
                print("无法从链接中解析出日期，将使用当前日期。")
                news_date = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")

            res =  {
                "news_date": news_date,
                "news_links": [item.get("news_links","") for item in news_data_list[1:]],
                "news_list_detail": [
                    {
                        "url": item.get("news_links", ""),
                        "title": item.get("title", "")
                    } for item in news_data_list[1:]
                ],
                "img_urls": [item.get("img_urls","") for item in news_data_list[1:]]
            }
            # pprint.pprint(res)

            return  res

    except Exception as e:
        print(f"抓取新闻数据时发生错误: {e}")

    return None



@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=10),
    retry=retry_if_exception_type((ConnectTimeout, ReadTimeout, RemoteProtocolError))
)
def fetch_item_content(news_url_title: {}):
    url = news_url_title.get("url")
    title = news_url_title.get("title")
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    response.raise_for_status()
    res= None
    if response.text:
        # # 使用更健壮的正则，即使找不到“编辑：”也能继续
        match = re.search(r"主要内容(.*?)(?:编辑：|$)", response.text, re.DOTALL)
        if match:
            html_doc = match.group(1).strip()
            # 转换 HTML 为 Markdown
            # heading_style="ATX" 意思是使用 # 风格的标题
            markdown_text = md(html_doc, heading_style="ATX")
            text_to_remove = '**央视网消息**（新闻联播）：'
            cleaned_text = markdown_text.replace(text_to_remove, '', 1)
            title_to_remove = "[视频]"
            cleaned_title = title.replace(title_to_remove, '', 1)
            res =  {
                "title": cleaned_title,
                "content": cleaned_text
            }

    return res



if __name__ == '__main__':

    data = fetch_news_data()
    pprint.pprint(data)
    if  data:
        for item in data.get("news_list_detail")[:2]:
            res = fetch_item_content(item)
            print(res)

