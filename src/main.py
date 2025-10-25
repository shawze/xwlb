import asyncio
import markdown
import datetime
from zoneinfo import ZoneInfo
import os
import sys
import json

# --- 路径和配置 ---
# 确保项目根目录在sys.path中
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 模块导入
from src.config import STAGE_CONFIG # 导入外部配置
from src.config import global_config
from src.services.cctv_fetcher import fetch_news_data, fetch_item_content
from src.services.gemini_analyzer_proxy import analyze_news_with_gemini
from src.services.wechat_clients import WeChatWorkClient, WeChatMPClient
from src.services.xueqiu import XueqiuPublisher
from src.utils.image_processor import download_selected_images, create_image_grid

# --- 全局常量 ---
IMAGES_OUTPUT_DIR = os.path.join(project_root, 'images', 'collages')
NEWS_DATA_CACHE_PATH = os.path.join(project_root, 'news_data.json')


async def main_workflow():
    """ 
    执行从内容获取到多平台发布的完整自动化工作流。
    该工作流被设计为可恢复的，会根据news_data.json的当前状态决定从哪个阶段开始执行。
    """
    print("--- 工作流启动 ---")

    # --- [阶段 1/5] 数据加载与状态检查 ---
    print("\n--- [1/5] 数据加载与状态检查 ---")
    news_data = None
    # --- 缓存检查 ---
    use_cache = False
    # 除非强制获取，否则尝试从本地缓存加载数据
    if os.path.exists(NEWS_DATA_CACHE_PATH) and not STAGE_CONFIG.get("force_fetch_news", False):
        print(f">>> 发现本地缓存: {NEWS_DATA_CACHE_PATH}，尝试加载...")
        try:
            with open(NEWS_DATA_CACHE_PATH, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
                use_cache = True
            # 基本完整性检查：确保核心数据存在
            if not news_data.get("news_date") or not news_data.get("news_links"):
                print(">>> [警告] 缓存数据不完整 (缺少日期或链接)，将触发全新获取。")
                news_data = None

            # 本地数据，新闻时间判断
            news_date_local_str = news_data.get("news_date")
            fetch_timestamp_str = news_data.get("fetch_timestamp")
            # 确保缓存中存在必要的日期和时间戳信息
            if news_date_local_str and fetch_timestamp_str:
                news_date_local = datetime.datetime.strptime(news_date_local_str, "%Y-%m-%d")
                news_date_local = news_date_local.replace(hour=20, second=0, microsecond=0, tzinfo=ZoneInfo( "Asia/Shanghai"))
                fetch_time = datetime.datetime.fromisoformat(fetch_timestamp_str)
                now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
                # 修正逻辑：如果当前时间还没有到第二天新闻联播的时间，则认为缓存有效
                if now < news_date_local + datetime.timedelta(days=1):
                    print(f">>> 数据为 {fetch_time.strftime('%Y-%m-%d %H:%M:%S')} 获取，仍在有效期内，使用本地缓存。")
                else:
                    print(f">>> 缓存数据过旧 ({fetch_time.strftime('%Y-%m-%d %H:%M:%S')})，将重新获取。")
                    news_data = None
            else:
                print(">>> 缓存中缺少必要日期信息，将重新获取。")

        except (json.JSONDecodeError, IOError) as e:
            print(f">>> [错误] 读取或解析缓存文件失败: {e}，将触发全新获取。")
            news_data = None
    
    if news_data:
        print(">>> 缓存加载成功。")
    else:
        if STAGE_CONFIG.get("force_fetch_news", False):
            print(">>> `force_fetch_news` 已激活，将强制执行全新获取流程。")
        else:
            print(">>> 未找到有效缓存，开始全新获取流程。")

    # --- [阶段 2/5] 内容获取 ---
    print("\n--- [2/5] 内容获取 ---")
    # 2.1 获取新闻列表 (仅在数据完全缺失时运行)
    if not news_data:
        print(">>> [2.1] 正在获取新闻列表...")
        try:
            fetched_data =  fetch_news_data()
            if fetched_data:
                news_data = fetched_data
                news_data['fetch_timestamp'] = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                with open(NEWS_DATA_CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(news_data, f, ensure_ascii=False, indent=4)
                print(f">>> 成功: 新闻列表已获取并存入缓存。")
            else:
                print(">>> [失败] 未能获取新闻列表，工作流终止。")
                return
        except Exception as e:
            print(f">>> [失败] 获取新闻列表时发生错误: {e}，工作流终止。")
            return
    else:
        print(">>> [2.1] 跳过获取新闻列表 (已存在)。")

    # 2.2 获取新闻详细内容
    if "contents" not in news_data or STAGE_CONFIG.get("force_fetch_contents", False):
        print(">>> [2.2] 正在获取新闻详细内容...")
        if STAGE_CONFIG.get("force_fetch_contents", False) and "contents" in news_data:
            print("    `force_fetch_contents` 已激活，强制重新获取。")
        
        news_links = news_data.get("news_list_detail", [])
        items_to_fetch = news_links
        
        news_contents = [fetch_item_content(item) for item in items_to_fetch]

        # 处理结果，过滤掉None和异常
        valid_contents = []
        for item in news_contents:
            if isinstance(item, Exception):
                print(f"    [警告] 一个新闻详细内容抓取失败: {item}")
            elif item:
                valid_contents.append(item)
        
        news_data['contents'] = valid_contents
        with open(NEWS_DATA_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)
        print(f">>> 成功: 获取了 {len(valid_contents)} 条新闻的详细内容并存入缓存。")
    else:
        print(">>> [2.2] 跳过获取新闻详细内容 (已存在)。")

    # --- [阶段 3/5] AI分析 ---
    print("\n--- [3/5] AI分析 ---")
    valid_contents = news_data.get("contents", [])
    analysis_text = news_data.get("analysis")

    if ("analysis" not in news_data or STAGE_CONFIG.get("force_rerun_analysis", False)) and valid_contents:
        print(">>> 正在进行AI分析...")
        if STAGE_CONFIG.get("force_rerun_analysis", False) and "analysis" in news_data:
            print("    `force_rerun_analysis` 已激活，强制重新分析。")
        try:
            generated_analysis =  analyze_news_with_gemini(valid_contents)
            if generated_analysis:
                analysis_text = generated_analysis
                news_data['analysis'] = analysis_text
                with open(NEWS_DATA_CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(news_data, f, ensure_ascii=False, indent=4)
                print(">>> 成功: AI分析完成并存入缓存。")
            else:
                print(">>> [失败] AI分析未能生成有效内容。")
        except Exception as e:
            print(f">>> [失败] AI分析阶段发生错误: {e}")
    else:
        if not valid_contents:
            print(">>> 跳过AI分析 (缺少新闻内容)。")
        else:
            print(">>> 跳过AI分析 (已存在)。")

    # --- [阶段 4/5] 封面图生成与上传 ---
    print("\n--- [4/5] 封面图生成与上传 ---")
    news_date = news_data.get("news_date")
    img_urls = news_data.get("img_urls", [])
    mp_thumb_media_id = news_data.get("mp_thumb_media_id")
    work_thumb_media_id = news_data.get("work_thumb_media_id")

    if ("mp_thumb_media_id" not in news_data or "work_thumb_media_id" not in news_data or STAGE_CONFIG.get("force_regenerate_cover", False)) and img_urls:
        if STAGE_CONFIG.get("force_regenerate_cover", False):
            print(">>> `force_regenerate_cover` 已激活，强制重新生成和上传封面。")
        
        # 4.1 查找或生成封面图
        print(">>> [4.1] 正在查找或生成封面图...")
        collage_path = None
        if news_date and use_cache:
            date_prefix = "collage_" + news_date.replace("-", "")
            try:
                if os.path.exists(IMAGES_OUTPUT_DIR):
                    matching_collages = sorted([f for f in os.listdir(IMAGES_OUTPUT_DIR) if f.startswith(date_prefix) and f.endswith(".jpg")])
                    if matching_collages:
                        collage_path = os.path.join(IMAGES_OUTPUT_DIR, matching_collages[-1])
                        print(f"    从本地找到匹配的封面图: {matching_collages[-1]}")
            except Exception as e:
                print(f"    [错误] 查找缓存封面图时出错: {e}")

        if not collage_path:
            print("    未找到本地封面，开始创建新封面...")
            try:
                os.makedirs(IMAGES_OUTPUT_DIR, exist_ok=True)
                downloaded_images = await download_selected_images(img_urls)
                if len(downloaded_images) >= 6:
                    timestamp = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
                    collage_filename = f"collage_{timestamp}.jpg"
                    collage_path = os.path.join(IMAGES_OUTPUT_DIR, collage_filename)
                    create_image_grid(downloaded_images, output_path=collage_path)
                    print(f"    成功: 新封面图已生成: {collage_filename}")
                else:
                    print("    可用图片不足6张，使用默认封面。")
                    collage_path = os.path.join(project_root, 'images', 'default_cover.png')
            except Exception as e:
                print(f"    [错误] 生成封面图过程中出错: {e}")

        # 4.2 上传封面图
        if collage_path and os.path.exists(collage_path):
            print(">>> [4.2] 正在上传封面图...")
            media_ids_updated = False
            # --- 微信公众号封面上传 ---
            if "mp_thumb_media_id" not in news_data or STAGE_CONFIG.get("force_regenerate_cover", False):
                try:
                    print("    正在为公众号上传封面图...")
                    mp_client = WeChatMPClient()
                    mp_thumb_media_id = mp_client.upload_image(collage_path)
                    news_data['mp_thumb_media_id'] = mp_thumb_media_id
                    print(f"    成功: 公众号封面图上传成功，Media ID: {mp_thumb_media_id}")
                    media_ids_updated = True
                except Exception as e:
                    print(f"    [错误] 上传封面图至公众号时出错: {e}")
            else:
                print("    公众号封面图Media ID已存在，跳过上传。")

            # --- 企业微信封面上传 ---
            if "work_thumb_media_id" not in news_data or STAGE_CONFIG.get("force_regenerate_cover", False):
                try:
                    print("    正在为企业微信上传封面图...")
                    work_client = WeChatWorkClient()
                    work_thumb_media_id = work_client.upload_temp_image(collage_path)
                    news_data['work_thumb_media_id'] = work_thumb_media_id
                    print(f"    成功: 企业微信封面图上传成功，Media ID: {work_thumb_media_id}")
                    media_ids_updated = True
                except Exception as e:
                    print(f"    [错误] 上传封面图至企业微信时出错: {e}")
            else:
                print("    企业微信封面图Media ID已存在，跳过上传。")
            
            if media_ids_updated:
                with open(NEWS_DATA_CACHE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(news_data, f, ensure_ascii=False, indent=4)
                print(">>> 成功: Media IDs已更新并存入缓存。")
        else:
            print(">>> [失败] 无可用封面图，跳过上传。")
    else:
        if not img_urls:
            print(">>> 跳过封面图生成与上传 (无图片链接)。")
        else:
            print(">>> 跳过封面图生成与上传 (Media IDs已存在)。")

    # --- [阶段 5/5] 多平台发布 ---
    print("\n--- [5/5] 多平台发布 ---")
    msg_title = f"{news_date} 新闻联播解读" if news_date else "新闻联播解读 (默认标题)"
    
    if not analysis_text:
        print(">>> [失败] 无AI分析内容，无法发布。工作流终止。")
        return

    is_eligible_for_auto_publish = False
    if news_data.get("fetch_timestamp"):
        fetch_time = datetime.datetime.fromisoformat(news_data["fetch_timestamp"])
        now = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
        if now - fetch_time < datetime.timedelta(hours=24):
            is_eligible_for_auto_publish = True

    should_publish_work = (is_eligible_for_auto_publish and not news_data.get("work_publish_timestamp")) or STAGE_CONFIG.get("force_publish_work", False)
    should_publish_mp = (is_eligible_for_auto_publish and not news_data.get("mp_publish_timestamp")) or STAGE_CONFIG.get("force_publish_mp", False)
    should_publish_xueqiu = (is_eligible_for_auto_publish and not news_data.get("xueqiu_publish_timestamp")) or STAGE_CONFIG.get("force_publish_xueqiu", False)

    # 准备HTML内容 (用于微信)
    html_content = markdown.markdown(analysis_text)
    clean_html_content = html_content.replace("\n", "").replace("\r", "").strip()
    qr_code_url = "https://mmbiz.qpic.cn/sz_mmbiz_png/oJkJlLSQ7U2ibmnVgKW2PzL3oicrSta2njI9ghvUiaghV3p1g9oHKTagyqN3iacwswMRDOjJibnKsbK1Z0AzfMcoUDQ/640?wx_fmt=png&amp"
    fill_html = "<section><span><br></span></section>"
    html_qrcode = f'<div><img src="{qr_code_url}"></div>'
    final_html_content = clean_html_content + fill_html + fill_html + html_qrcode
    print(">>> HTML内容已为微信平台生成。")

    publish_state_updated = False
    # a. 企业微信发布
    if STAGE_CONFIG.get("publish_wechat_work", False):
        print(">>> [5.1] 企业微信发布...")
        if should_publish_work:
            if work_thumb_media_id:
                try:
                    print("    正在发送到企业微信...")
                    work_client = WeChatWorkClient()
                    work_client.send_mpnews(title=msg_title, content=final_html_content, thumb_media_id=work_thumb_media_id)
                    print("    >>> 成功: 已发送到企业微信。")
                    news_data['work_publish_timestamp'] = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                    publish_state_updated = True
                except Exception as e:
                    print(f"    >>> [失败] 发送到企业微信时出错: {e}")
            else:
                print("    >>> 跳过发送，缺少封面 Media ID。")
        else:
            print("    >>> 跳过发送，数据不是新生成或未被强制发布。")
    else:
        print(">>> [5.1] 跳过企业微信发布 (配置已禁用)。")

    # b. 微信公众号发布
    if STAGE_CONFIG.get("publish_wechat_mp", False):
        print(">>> [5.2] 微信公众号发布...")
        if should_publish_mp:
            if mp_thumb_media_id:
                try:
                    print("    \n正在创建微信公众号草稿...")
                    mp_client = WeChatMPClient()
                    mp_client.create_draft(title=msg_title, content=final_html_content, thumb_media_id=mp_thumb_media_id)
                    print("    >>> 成功: 微信公众号草稿已创建。")
                    news_data['mp_publish_timestamp'] = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                    publish_state_updated = True
                except Exception as e:
                    print(f"    >>> [失败] 创建微信公众号草稿时出错: {e}")
            else:
                print("    >>> 跳过创建草稿，缺少封面 Media ID。")
        else:
            print("    >>> 跳过创建草稿，数据不是新生成或未被强制发布。")
    else:
        print(">>> [5.2] 跳过微信公众号发布 (配置已禁用)。")

    # c. 雪球发布
    html_xuqiu = f'<div><strong>关注微信公众号,每日定时更新: Cloudify </strong></div>'
    xuqiu_html_content = html_xuqiu + fill_html + fill_html + clean_html_content + fill_html + fill_html + html_xuqiu

    if STAGE_CONFIG.get("publish_xueqiu", False):
        print(">>> [5.3] 雪球发布...")
        if should_publish_xueqiu:
            xueqiu_cookie = global_config.get("XUEQIU","XUEQIU_COOKIE")
            if xueqiu_cookie:
                try:
                    print("    正在发布到雪球...")
                    publisher = XueqiuPublisher(
                        cookie=xueqiu_cookie,
                        title=msg_title,
                        content=xuqiu_html_content)
                    publisher.publish()
                    print("    >>> 成功: 已发布到雪球。")
                    news_data['xueqiu_publish_timestamp'] = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                    publish_state_updated = True
                except Exception as e:
                    print(f"    >>> [失败] 发布到雪球时出错: {e}")
            else:
                print("    >>> 跳过发布，缺少雪球 Cookie 配置。")
        else:
            print("    >>> 跳过发布，数据不是新生成或未被强制发布。")
    else:
        print(">>> [5.3] 跳过雪球发布 (配置已禁用)。")
    
    if publish_state_updated:
        with open(NEWS_DATA_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)
        print(f"\n>>> 成功: 发布状态已更新并存入缓存。")

    print("\n--- 工作流结束 ---")


if __name__ == "__main__":
    asyncio.run(main_workflow())
