"""
HR Manager Navigation Test Script
Tests that all pages load without 'Objects are not valid as React child' errors
"""
import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        test_results = []
        base_url = "https://unified-sow-builder.preview.emergentagent.com"
        
        # Step 1: Login
        print("=" * 60)
        print("STEP 1: Login as HR Manager (DVC037)")
        print("=" * 60)
        
        await page.goto(f"{base_url}/login")
        await page.wait_for_timeout(2000)
        
        inputs = await page.query_selector_all("input")
        if len(inputs) >= 2:
            await inputs[0].fill("DVC037")
            await inputs[1].fill("test123")
        
        await page.wait_for_timeout(500)
        
        login_btn = await page.query_selector("button[type='submit']")
        if login_btn:
            await login_btn.click()
        
        await page.wait_for_timeout(3000)
        
        if "login" in page.url:
            print("FAIL: Login failed")
            await browser.close()
            return
        
        print(f"PASS: Login successful - URL: {page.url}")
        test_results.append({"page": "HR Dashboard", "status": "PASS"})
        
        # Test pages
        pages = [
            {"name": "Employees", "url": "/employees"},
            {"name": "Attendance", "url": "/attendance"},
            {"name": "Payroll", "url": "/payroll"},
            {"name": "CTC Designer", "url": "/ctc-designer"},
            {"name": "Document Center", "url": "/document-center"},
            {"name": "Go-Live Dashboard", "url": "/go-live"},
            {"name": "Leave Management", "url": "/leave-management"},
        ]
        
        for p_info in pages:
            print(f"\n{'=' * 60}")
            print(f"TEST: Navigate to {p_info['name']}")
            print("=" * 60)
            
            try:
                await page.goto(f"{base_url}{p_info['url']}", wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(2000)
                
                print(f"  URL: {page.url}")
                
                if "login" in page.url:
                    print("  FAIL: Redirected to login")
                    test_results.append({"page": p_info["name"], "status": "FAIL", "reason": "Redirected to login"})
                    continue
                
                content = await page.content()
                
                if "Something went wrong" in content:
                    print("  FAIL: Error boundary triggered")
                    test_results.append({"page": p_info["name"], "status": "FAIL", "reason": "Error boundary"})
                    continue
                
                if "Objects are not valid" in content:
                    print("  FAIL: React rendering error")
                    test_results.append({"page": p_info["name"], "status": "FAIL", "reason": "React error"})
                    continue
                
                print(f"  PASS: {p_info['name']} loaded successfully")
                test_results.append({"page": p_info["name"], "status": "PASS"})
                
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                test_results.append({"page": p_info["name"], "status": "ERROR", "reason": str(e)})
        
        # Summary
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        
        passed = sum(1 for r in test_results if r["status"] == "PASS")
        failed = sum(1 for r in test_results if r["status"] == "FAIL")
        
        for r in test_results:
            icon = "PASS" if r["status"] == "PASS" else "FAIL"
            reason = r.get("reason", "OK")
            print(f"  [{icon}] {r['page']}: {reason}")
        
        print(f"\nPASSED: {passed}/{len(test_results)}")
        
        await browser.close()
        
        return test_results

if __name__ == "__main__":
    asyncio.run(run_test())
