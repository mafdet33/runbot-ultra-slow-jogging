# scrape_mohw_selenium.py
import time
import json
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# -----------------------
# 清理文字
# -----------------------
def clean(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# -----------------------
# Selenium 抓單篇全文
# -----------------------

def fetch_article(url):
    print(f"🥗 抓取文章：{url}")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get(url)
    time.sleep(2)

    # 嘗試抓文章內容
    candidates = [
        "#page-top",
        ".innerPage",
        ".content",
        "#ContentPlaceHolder1_pnlContent",
        "article",
    ]

    text = ""
    for c in candidates:
        try:
            el = driver.find_element(By.CSS_SELECTOR, c)
            raw = el.text
            if len(raw) > len(text):
                text = raw
        except:
            continue

    if not text or len(text) < 50:
        text = driver.find_element(By.TAG_NAME, "body").text

    # 嘗試抓標題
    title_candidates = [
        "h1",
        "h2",
        ".page-main-title",
        ".title",
    ]

    title = ""
    for c in title_candidates:
        try:
            t = driver.find_element(By.CSS_SELECTOR, c).text
            if t and len(t) > len(title):
                title = t
        except:
            continue

    # fallback
    if not title:
        title = driver.title

    driver.quit()

    return clean(title), clean(text)

# -----------------------
# 基本 NLP 分群
# -----------------------
def classify(text):
    text = text.lower()
    if any(k in text for k in ["迷思", "錯誤", "真假", "闢謠", "流言"]):
        return "闢謠"
    if any(k in text for k in ["老人", "長者", "銀髮", "跌倒"]):
        return "老人健康"
    if any(k in text for k in ["兒童", "小孩", "幼兒"]):
        return "兒童健康"
    if any(k in text for k in ["運動", "步道", "體能", "健走", "活動量"]):
        return "運動促進"
    if any(k in text for k in ["飲食", "營養", "脂肪", "熱量"]):
        return "飲食與營養"
    return "其他"


# -----------------------
# 抓某分類最新 10 篇文章 pid
# -----------------------
def fetch_latest_pids(list_url, limit=10):
    print(f"\n📄 抓取列表頁：{list_url}")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get(list_url)
    time.sleep(1)

    # 🔍 抓所有 Detail 連結
    elems = driver.find_elements(By.CSS_SELECTOR, "a")
    urls = []
    for e in elems:
        try:
            href = e.get_attribute("href")
            if href and "Detail.aspx" in href:
                urls.append(href)
        except:
            continue

    driver.quit()

    # 去重 + 只取最新 limit 篇
    urls = list(dict.fromkeys(urls))  
    urls = urls[:limit]
    print(f"✓ 抓到 {len(urls)} 篇")
    return urls


# -----------------------
# 主流程：每分類抓 10 篇
# -----------------------
def run():

    CATEGORY_LIST = {
        "老人健康": "https://www.hpa.gov.tw/Pages/List.aspx?nodeid=4625",
        "闢謠": "https://www.hpa.gov.tw/Pages/List.aspx?nodeid=127",
        "兒童健康": "https://www.hpa.gov.tw/Pages/List.aspx?nodeid=4477",
        "運動促進": "https://www.hpa.gov.tw/Pages/List.aspx?nodeid=40",
        "飲食與營養": "https://www.hpa.gov.tw/Pages/List.aspx?nodeid=37"
    }

    results = {}

    for cat, list_url in CATEGORY_LIST.items():
        print(f"\n=========================")
        print(f"📚 分類：{cat}")
        print(f"=========================")

        urls = fetch_latest_pids(list_url, limit=10)
        results[cat] = []

        for url in urls:
            try:
                title, content = fetch_article(url)
                results[cat].append({
                    "title": title,
                    "content": content,
                    "category": cat,
                    "url": url
                })
            except Exception as e:
                print(f"⚠️ 抓取失敗：{url}, error={e}")

    os.makedirs("content", exist_ok=True)
    with open("content/mohw_grouped.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n🎉 已產生 content/mohw_grouped.json")


if __name__ == "__main__":
    run()