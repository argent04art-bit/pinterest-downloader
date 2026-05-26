#!/usr/bin/env python3
"""
Pinterest Pin Downloader
ابزار ساده برای دانلود تصاویر از پینترست
"""

import aiohttp
import asyncio
import sys
import re
import os
from urllib.parse import urlparse, unquote

def extract_pin_id(pin_url):
    """
    استخراج شناسه پین از لینک پینترست
    پشتیبانی از فرمت‌های مختلف لینک:
    - https://pin.it/52EJKFD7S
    - https://www.pinterest.com/pin/123456789/
    - https://in.pinterest.com/pin/123456789/
    """
    # فرمت pin.it (لینک کوتاه شده)
    pin_short_match = re.search(r'pin\.it/([A-Za-z0-9]+)', pin_url)
    if pin_short_match:
        return pin_short_match.group(1)
    
    # فرمت معمولی /pin/123456789/
    pin_normal_match = re.search(r'/pin/(\d+)', pin_url)
    if pin_normal_match:
        return pin_normal_match.group(1)
    
    return None

async def get_pin_info(pin_id, session):
    """
    دریافت اطلاعات پین از API پینترست
    """
    # API غیررسمی پینترست (ممکن است در آینده تغییر کند)
    api_urls = [
        f"https://api.pinterest.com/v3/pidgets/pins/info/?pin_id={pin_id}",
        f"https://www.pinterest.com/resource/PinResource/get/?source_url=/pin/{pin_id}/&data=%7B%22options%22%3A%7B%22field_set_key%22%3A%22all%22%2C%22id%22%3A%22{pin_id}%22%7D%7D"
    ]
    
    for api_url in api_urls:
        try:
            async with session.get(api_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
        except:
            continue
    
    return None

def extract_image_url(data):
    """
    استخراج آدرس تصویر با کیفیت اصلی از دیتای دریافتی
    """
    # روش اول: ساختار API v3
    if 'data' in data:
        if 'images' in data['data']:
            images = data['data']['images']
            # اولویت: کیفیت اصلی (orig) -> high quality -> medium -> low
            if 'orig' in images:
                return images['orig']['url']
            elif '564x' in images:
                return images['564x']['url']
            elif '736x' in images:
                return images['736x']['url']
            elif '192x' in images:
                return images['192x']['url']
    
    # روش دوم: جستجوی مستقیم آدرس تصویر در دیتا
    data_str = str(data)
    url_pattern = r'https?://[^\s"\']+\.(jpg|jpeg|png|webp|mp4)[^\s"\']*'
    urls = re.findall(url_pattern, data_str, re.IGNORECASE)
    
    # فیلتر کردن آدرس‌های واقعی تصویر
    for url in urls:
        if isinstance(url, tuple):
            url = url[0] if url else None
        if url and ('pinimg.com' in url or 'pinterest.com' in url):
            # حذف پارامترهای اضافی
            clean_url = url.split('?')[0]
            return clean_url
    
    return None

async def download_file(session, url, filename):
    """
    دانلود فایل از آدرس مشخص
    """
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(filename, 'wb') as f:
                    f.write(await response.read())
                return True
            else:
                print(f"  ❌ خطا در دانلود: HTTP {response.status}")
                return False
    except Exception as e:
        print(f"  ❌ خطا: {e}")
        return False

async def main(pin_url):
    """
    تابع اصلی
    """
    print("=" * 60)
    print("📌 Pinterest Pin Downloader")
    print("=" * 60)
    print(f"🔗 آدرس: {pin_url}")
    print()
    
    # مرحله 1: استخراج شناسه پین
    print("🔍 مرحله 1: استخراج شناسه پین...")
    pin_id = extract_pin_id(pin_url)
    
    if not pin_id:
        print("❌ خطا: لینک معتبر نیست!")
        print("   لطفاً لینکی به فرمت زیر وارد کنید:")
        print("   - https://pin.it/XXXXXX")
        print("   - https://www.pinterest.com/pin/123456789/")
        return False
    
    print(f"   ✅ شناسه پین: {pin_id}")
    print()
    
    # مرحله 2: دریافت اطلاعات از API
    print("🌐 مرحله 2: اتصال به پینترست...")
    
    async with aiohttp.ClientSession() as session:
        pin_info = await get_pin_info(pin_id, session)
        
        if not pin_info:
            print("❌ خطا:无法 دریافت اطلاعات از پینترست!")
            print("   ممکن است پین خصوصی باشد یا حذف شده باشد.")
            return False
        
        print("   ✅ اطلاعات دریافت شد")
        print()
        
        # مرحله 3: استخراج آدرس تصویر
        print("🖼️ مرحله 3: یافتن آدرس تصویر با کیفیت اصلی...")
        image_url = extract_image_url(pin_info)
        
        if not image_url:
            print("❌ خطا: آدرس تصویری یافت نشد!")
            return False
        
        print(f"   ✅ آدرس یافت شد")
        print()
        
        # مرحله 4: دانلود فایل
        print("📥 مرحله 4: دانلود فایل...")
        
        # تعیین نام فایل
        extension = image_url.split('.')[-1].split('?')[0]
        if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4']:
            extension = 'jpg'
        
        filename = f"{pin_id}.{extension}"
        
        success = await download_file(session, image_url, filename)
        
        if success:
            # دریافت حجم فایل
            file_size = os.path.getsize(filename)
            size_kb = file_size / 1024
            size_mb = size_kb / 1024
            
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{size_kb:.2f} KB"
            
            print()
            print("=" * 60)
            print(f"✅ دانلود با موفقیت انجام شد!")
            print(f"📁 نام فایل: {filename}")
            print(f"📦 حجم: {size_str}")
            print("=" * 60)
            return True
        else:
            print()
            print("❌ دانلود ناموفق بود!")
            return False

if __name__ == "__main__":
    # بررسی آرگومان‌های خط فرمان
    if len(sys.argv) < 2:
        print("❗ نحوه استفاده:")
        print(f"   python {sys.argv[0]} <آدرس_پین>")
        print()
        print("مثال:")
        print(f"   python {sys.argv[0]} https://pin.it/52EJKFD7S")
        sys.exit(1)
    
    pin_url = sys.argv[1]
    
    # اجرای تابع اصلی
    try:
        success = asyncio.run(main(pin_url))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ عملیات توسط کاربر لغو شد.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطای پیش‌بینی نشده: {e}")
        sys.exit(1)
