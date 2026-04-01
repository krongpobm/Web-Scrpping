import asyncio
import json
import re
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

sys.stdout.reconfigure(encoding='utf-8')

def parse_company_info(text: str) -> dict:
    """Parse card_0: general company information (key-value pairs on alternating lines)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    info = {}
    # Known labels in order
    labels = [
        "ประเภทนิติบุคคล", "สถานะนิติบุคคล", "วันที่จดทะเบียนจัดตั้ง",
        "ทุนจดทะเบียน", "เลขทะเบียนเดิม", "กลุ่มธุรกิจ", "ขนาดธุรกิจ",
        "ปีที่ส่งงบการเงิน", "ที่ตั้งสำนักงานแห่งใหญ่", "Website",
    ]
    i = 0
    while i < len(lines):
        if lines[i] in labels:
            label = lines[i]
            # collect value lines until next label or end
            val_parts = []
            i += 1
            while i < len(lines) and lines[i] not in labels and "คลิกที่ปี" not in lines[i]:
                val_parts.append(lines[i])
                i += 1
            info[label] = " ".join(val_parts).strip()
        else:
            i += 1
    # Clean up year list
    if "ปีที่ส่งงบการเงิน" in info:
        years = re.findall(r'\d{4}', info["ปีที่ส่งงบการเงิน"])
        info["ปีที่ส่งงบการเงิน"] = years
    return info

def parse_directors(text: str) -> list:
    """Parse card_1: list of directors."""
    lines = [l.strip().rstrip('/') for l in text.splitlines() if l.strip()]
    return lines

def parse_signing_authority(text: str) -> str:
    """Parse card_2: signing authority description."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(lines).rstrip('/')

def parse_business_types(texts: list) -> list:
    """Parse card_3, card_4, ... : business type cards."""
    results = []
    for text in texts:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        entry = {}
        for i, line in enumerate(lines):
            if line == "ประเภทธุรกิจ" and i + 1 < len(lines):
                entry["ประเภทธุรกิจ"] = lines[i + 1]
            if line == "วัตถุประสงค์" and i + 1 < len(lines):
                entry["วัตถุประสงค์"] = lines[i + 1]
        if entry:
            results.append(entry)
    return results

async def main():
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                locale='th-TH',
            )
            page = await context.new_page()

            profile_url = "https://datawarehouse.dbd.go.th/company/profile/50105545071341"
            print(f"Navigating to: {profile_url}")
            await page.wait_for_timeout(2000)
            await page.goto(profile_url, wait_until="networkidle")
            await page.wait_for_timeout(5000)

            # --- Scrape company name from page heading ---
            company_name = ""
            try:
                company_name = (await page.locator("h4, h3, .company-name, .juristic-name").first.inner_text()).strip()
            except Exception:
                pass

            # --- Scrape registration number from URL or page ---
            reg_no = profile_url.rstrip("/").split("/")[-1]

            # --- Collect all card-body texts ---
            cards = await page.locator(".card-body").all_inner_texts()

            await browser.close()

        # --- Parse cards into structured data ---
        result = {
            "url": profile_url,
            "เลขนิติบุคคล": reg_no,
            "ชื่อบริษัท": company_name,
        }

        if len(cards) > 0:
            result["ข้อมูลทั่วไป"] = parse_company_info(cards[0])
        if len(cards) > 1:
            result["กรรมการ"] = parse_directors(cards[1])
        if len(cards) > 2:
            result["อำนาจกระทำการ"] = parse_signing_authority(cards[2])
        if len(cards) > 3:
            # card_3 and card_4 are business type cards; card_5 is disclaimer
            business_cards = [c for c in cards[3:] if "ประเภทธุรกิจ" in c]
            result["ประเภทธุรกิจ"] = parse_business_types(business_cards)

        # --- Save to JSON ---
        output_file = "company_profile.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✅ บันทึกข้อมูลเป็น {output_file} สำเร็จ")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"Outer Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())