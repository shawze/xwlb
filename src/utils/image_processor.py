import asyncio
import httpx
import random
import io
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from PIL import Image, ImageOps
except ImportError:
    print("错误: Pillow 库未安装。请在终端运行 'pip install Pillow' 来安装它。")
    exit(1)

# --- 配置项 ---
THUMBNAIL_SIZE = (200, 200)
GRID_COLS = 3
GRID_ROWS = 2
IMAGES_NEEDED = GRID_COLS * GRID_ROWS

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True
)
async def download_image_with_retry(client: httpx.AsyncClient, url: str):
    """使用重试机制异步下载单个图片。"""
    # print(f"尝试下载: {url}")
    response = await client.get(url, timeout=20.0)
    response.raise_for_status()
    return response.content

async def _download_images_concurrently(client: httpx.AsyncClient, image_urls: List[str]) -> List[bytes]:
    """内部辅助函数：并发下载一系列图片，并优雅地处理失败任务。"""
    tasks = [download_image_with_retry(client, url) for url in image_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    image_bytes_list = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"下载最终失败 {image_urls[i]}: {repr(result)}")
        else:
            # print(f"下载成功: {image_urls[i]}")
            image_bytes_list.append(result)
            
    return image_bytes_list

async def download_selected_images(image_urls: List[str]) -> List[bytes]:
    """
    从给定的图片URL列表中，优先选择IMAGES_NEEDED张进行下载。
    如果下载失败，则从剩余链接中继续尝试，直到达到所需数量或所有链接尝试完毕。
    """
    downloaded_images_bytes = []
    remaining_urls = list(image_urls) # 复制一份，避免修改原始列表

    async with httpx.AsyncClient() as client:
        while len(downloaded_images_bytes) < IMAGES_NEEDED and remaining_urls:
            # 还需要下载的图片数量
            num_to_select = IMAGES_NEEDED - len(downloaded_images_bytes)
            
            # 随机选择要尝试下载的URL，数量不超过剩余URL数
            urls_to_try = random.sample(remaining_urls, min(num_to_select, len(remaining_urls)))
            
            print(f"尝试从 {len(remaining_urls)} 个链接中下载 {len(urls_to_try)} 张图片...")
            
            # 并发下载选定的图片
            newly_downloaded = await _download_images_concurrently(client, urls_to_try)
            downloaded_images_bytes.extend(newly_downloaded)
            
            # 从剩余URL中移除已尝试的URL
            remaining_urls = [url for url in remaining_urls if url not in urls_to_try]
            
            if not newly_downloaded and remaining_urls:
                print("本次尝试未能下载任何新图片，且仍有剩余链接，继续尝试...")
            elif not remaining_urls and len(downloaded_images_bytes) < IMAGES_NEEDED:
                print(f"所有可用链接已尝试完毕，但未能下载到足够的 {IMAGES_NEEDED} 张图片。")
                break

    if len(downloaded_images_bytes) < IMAGES_NEEDED:
        print(f"警告: 最终只成功下载了 {len(downloaded_images_bytes)} 张图片，未能达到所需的 {IMAGES_NEEDED} 张。")
    
    return downloaded_images_bytes


def create_image_grid(image_bytes_list: List[bytes], output_path: str = "collage.jpg") -> str:
    """
    从给定的图片二进制列表中，通过裁剪来填充单元格，创建一个无缝的3x2网格图片并保存。
    此函数假定 image_bytes_list 已经包含了所需数量 (IMAGES_NEEDED) 的图片。
    """
    if len(image_bytes_list) < IMAGES_NEEDED:
        raise ValueError(f"创建网格需要至少 {IMAGES_NEEDED} 张图片, 但只提供了 {len(image_bytes_list)} 张。")

    print(f"开始处理 {IMAGES_NEEDED} 张已下载的图片以创建网格...")
    processed_images = []
    for img_bytes in image_bytes_list: # 直接使用传入的列表，不再随机选择
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            cropped_thumb = ImageOps.fit(img, THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            processed_images.append(cropped_thumb)
        except Exception as e:
            print(f"处理一张图片时失败: {e}")

    if len(processed_images) < IMAGES_NEEDED:
        raise ValueError(f"能成功处理的图片少于 {IMAGES_NEEDED} 张，无法创建网格。")

    total_width = THUMBNAIL_SIZE[0] * GRID_COLS
    total_height = THUMBNAIL_SIZE[1] * GRID_ROWS
    grid_image = Image.new('RGB', (total_width, total_height))

    print("开始将6张裁剪后的图片拼接到一张大图上...")
    for index, thumb in enumerate(processed_images):
        row = index // GRID_COLS
        col = index % GRID_COLS
        x_offset = col * THUMBNAIL_SIZE[0]
        y_offset = row * THUMBNAIL_SIZE[1]
        grid_image.paste(thumb, (x_offset, y_offset))

    grid_image.save(output_path)
    print(f"成功！无缝拼接的图片已保存至: {output_path}")
    return output_path