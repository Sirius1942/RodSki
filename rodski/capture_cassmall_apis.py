#!/usr/bin/env python3
"""
Cassmall API Capture Script
使用 Playwright 捕获 cassmall 前后端分离的真实接口
"""
from playwright.sync_api import sync_playwright
import json
import time

OUTPUT_DIR = "/Users/sirius.chen/Documents/projects/lightning-strike-team/cassmall/thdh/rod_ski_format"

def capture_seller_apis():
    """捕获商家端接口"""
    print("=" * 60)
    print("阶段1：捕获商家端接口（小辉 13395432251）")
    print("=" * 60)
    
    captured = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        patterns = ['/api/', '/web-api/', '/merchant/', '/seller/']
        
        def handle_request(req):
            for pat in patterns:
                if pat in req.url:
                    captured.append({
                        'url': req.url,
                        'method': req.method,
                        'post_data': req.post_data,
                        'resource_type': req.resource_type
                    })
                    break
        
        page.on('request', handle_request)
        
        # 1. 登录商家端
        print("1. 登录商家端...")
        page.goto('https://ec-hwbeta.casstime.com/passport/login', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        try:
            page.click('span[type=PASSWORD]')
            time.sleep(0.5)
        except:
            print("   跳过账号tab点击")
        
        page.fill('#userName', '13395432251')
        page.fill('#password', 'Cass2025')
        
        try:
            page.click('label.br-checkbox')
            time.sleep(0.5)
        except:
            print("   跳过同意协议")
        
        page.click('.btn-submit')
        time.sleep(5)
        
        print(f"   登录后 URL: {page.url}")
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 2. 访问入库单列表页
        print("2. 访问入库单列表页...")
        page.goto('https://ec-hwbeta.casstime.com/seller#/merchant/warehouse-entry/list', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 3. 访问订单管理
        print("3. 访问订单管理...")
        page.goto('https://ec-hwbeta.casstime.com/seller#/order/list', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 4. 访问商品管理
        print("4. 访问商品管理...")
        page.goto('https://ec-hwbeta.casstime.com/seller#/product/list', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        browser.close()
    
    print(f"\n商家端总计捕获: {len(captured)} 个接口请求")
    
    # 保存结果
    output_file = f"{OUTPUT_DIR}/captured_seller_apis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print(f"商家端接口已保存: {output_file}")
    
    return captured


def capture_market_apis():
    """捕获维修厂端接口"""
    print("\n" + "=" * 60)
    print("阶段2：捕获维修厂端接口（小李 15521344075）")
    print("=" * 60)
    
    captured = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        patterns = ['/api/', '/web-api/', '/market/', '/agent/']
        
        def handle_request(req):
            for pat in patterns:
                if pat in req.url:
                    captured.append({
                        'url': req.url,
                        'method': req.method,
                        'post_data': req.post_data,
                        'resource_type': req.resource_type
                    })
                    break
        
        page.on('request', handle_request)
        
        # 1. 登录维修厂端
        print("1. 登录维修厂端...")
        page.goto('https://ec-hwbeta.casstime.com/passport/login', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        try:
            page.click('span[type=PASSWORD]')
            time.sleep(0.5)
        except:
            print("   跳过账号tab点击")
        
        page.fill('#userName', '15521344075')
        page.fill('#password', 'Cass2025')
        
        try:
            page.click('label.br-checkbox')
            time.sleep(0.5)
        except:
            print("   跳过同意协议")
        
        page.click('.btn-submit')
        time.sleep(5)
        
        print(f"   登录后 URL: {page.url}")
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 2. 访问首页
        print("2. 访问维修厂首页...")
        page.goto('https://ec-hwbeta.casstime.com/market/portal', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 3. 访问询价页面
        print("3. 访问询价页面...")
        page.goto('https://ec-hwbeta.casstime.com/market/agentBuy/', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 4. 访问购物车
        print("4. 访问购物车...")
        page.goto('https://ec-hwbeta.casstime.com/market/cart', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        # 5. 访问订单列表
        print("5. 访问订单列表...")
        page.goto('https://ec-hwbeta.casstime.com/market/order/list', wait_until='networkidle', timeout=30000)
        time.sleep(4)
        print(f"   已捕获: {len(captured)} 个请求")
        
        browser.close()
    
    print(f"\n维修厂端总计捕获: {len(captured)} 个接口请求")
    
    # 保存结果
    output_file = f"{OUTPUT_DIR}/captured_market_apis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print(f"维修厂端接口已保存: {output_file}")
    
    return captured


def main():
    seller_apis = capture_seller_apis()
    market_apis = capture_market_apis()
    
    print("\n" + "=" * 60)
    print("捕获完成!")
    print(f"商家端接口: {len(seller_apis)} 个")
    print(f"维修厂端接口: {len(market_apis)} 个")
    print("=" * 60)


if __name__ == '__main__':
    main()
