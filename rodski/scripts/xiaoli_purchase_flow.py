#!/usr/bin/env python3
"""
小李（维修厂）完整下单流程 - 录制视频
流程：登录 → 发布询价 → 填写配件 → 提交询价 → 查看报价 → 下采购订单
"""
import asyncio
import os
import time
from playwright.async_api import async_playwright

RECORDING_DIR = "screenshots/cassmall-beta/recording"
SCREENSHOT_DIR = "screenshots/cassmall-beta"
os.makedirs(RECORDING_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def run_xiaoli_purchase_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=RECORDING_DIR
        )
        page = await context.new_page()
        
        # ===== 第1步：登录 =====
        print("=== 步骤1: 登录 ===")
        await page.goto("https://ec-hwbeta.casstime.com/passport/login")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_login_page.png")
        
        # 切换到账号登录（使用JS）
        await page.evaluate("changeLoginWay(document.querySelector('span[type=PASSWORD]'))")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_account_tab.png")
        
        # 填写用户名密码
        await page.fill("#userName", "15521344075")
        await page.fill("#password", "Cass2025")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_credentials.png")
        
        # 勾选协议
        await page.evaluate("document.querySelector('label.br-checkbox input[type=checkbox]').click()")
        await page.wait_for_timeout(300)
        
        # 提交登录
        await page.evaluate("document.querySelector('.btn-submit').click()")
        await page.wait_for_timeout(8000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_after_login.png")
        print(f"登录后URL: {page.url}")
        
        # 保存登录状态
        await context.storage_state(path=f"{SCREENSHOT_DIR}/xiaoli_state.json")
        
        # ===== 第2步：进入商城首页 =====
        print("=== 步骤2: 进入商城首页 ===")
        await page.goto("https://ec-hwbeta.casstime.com/market/portal")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/05_mall_home.png")
        
        # ===== 第3步：进入发布询价页面 =====
        print("=== 步骤3: 进入发布询价 ===")
        await page.goto("https://ec-hwbeta.casstime.com/agentBuy/")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/06_inquiry_page.png")
        
        # ===== 第4步：填写配件信息 =====
        print("=== 步骤4: 填写配件信息 ===")
        
        # 尝试按品类选择
        category_btn = await page.query_selector("text=按品类选择")
        if category_btn:
            await category_btn.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/07_category_dialog.png")
            print("点击了按品类选择")
        
        # 关闭弹窗
        try:
            close_btn = await page.query_selector("button:has-text('取消'), button:has-text('关闭')")
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # ===== 第5步：尝试提交询价 =====
        print("=== 步骤5: 提交询价 ===")
        # 查找提交/发布询价的按钮
        submit_btn = await page.query_selector("text=提交询价")
        if not submit_btn:
            submit_btn = await page.query_selector("text=发布询价")
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/08_after_submit.png")
            print("点击了提交询价")
        
        # ===== 第6步：跳转到查看报价 =====
        print("=== 步骤6: 查看报价 ===")
        await page.goto("https://ec-hwbeta.casstime.com/agentBuy/quotationList")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/09_quotation_list.png")
        
        # ===== 第7步：进入我的订单 =====
        print("=== 步骤7: 我的订单 ===")
        await page.goto("https://ec-hwbeta.casstime.com/agentBuy/orderList")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/10_order_list.png")
        
        # 等待一下让视频录制完整
        await page.wait_for_timeout(2000)
        
        # 完成
        print("=== 流程完成 ===")
        print(f"视频保存位置: {RECORDING_DIR}")
        
        # 不关闭浏览器，让视频保存
        await page.wait_for_timeout(3000)
        
        # 获取视频文件
        video = page.video
        if video:
            video_path = f"{RECORDING_DIR}/purchase_flow.webm"
            await video.save_as(video_path)
            print(f"视频已保存: {video_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_xiaoli_purchase_flow())