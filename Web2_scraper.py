import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def scrape_dbd(keyword):
    async with async_playwright() as p:
        # 1. เปิด Browser
        browser = await p.chromium.launch(headless=False) # ตั้งเป็น False เพื่อดูการทำงานจริง
        context = await browser.new_context()
        page = await context.new_page()
        
        # ใช้ Stealth เพื่อไม่ให้เว็บรู้ว่าเป็น Bot
        await stealth_async(page)

        # 2. ไปที่หน้าเว็บ
        print(f"กำลังเข้าหน้าเว็บเพื่อค้นหา: {keyword}...")
        await page.goto("https://datawarehouse.dbd.go.th/index")
        
        # 3. พิมพ์คำค้นหาและกด Enter
        # หมายเหตุ: Selector เหล่านี้อาจต้องเปลี่ยนตามโครงสร้างเว็บจริง ณ ขณะนั้น
        await page.fill('input#searchCondition', keyword) 
        await page.keyboard.press("Enter")
        
        # รอให้ตารางข้อมูลโหลดเสร็จ
        await page.wait_for_selector('table#example') 
        
        # 4. ดึงข้อมูลจากตาราง
        rows = await page.query_selector_all('table#example tbody tr')
        results = []

        for row in rows:
            cols = await row.query_selector_all('td')
            if len(cols) > 1:
                col_0 = await cols[0].inner_text()
                col_1 = await cols[1].inner_text()
                col_2 = await cols[2].inner_text()
                col_3 = await cols[3].inner_text()
                col_4 = await cols[4].inner_text()
                
                data = {
                    "no": col_0.strip(),
                    "regNo": col_1.strip(),
                    "companyNameTh": col_2.strip(),
                    "status": col_3.strip(),
                    "province": col_4.strip()
                }
                results.append(data)

        # 5. แปลงเป็น JSON format
        final_json = {
            "success": True,
            "keyword": keyword,
            "total": len(results),
            "companies": results
        }
        
        await browser.close()
        return final_json

async def main():
    output = await scrape_dbd("SCGJWD")
    
    # บันทึกลงไฟล์ .json
    with open('dbd_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print("ดึงข้อมูลสำเร็จ! บันทึกไฟล์เป็น dbd_data.json แล้ว")

# เรียกใช้งาน
if __name__ == "__main__":
    asyncio.run(main())