import SwiftUI

/// RodSki iOS Demo App 入口。
///
/// 与 Android Demo（com.rodski.demo）一一对齐的最小 SwiftUI 应用，
/// 演示 登录 → 主页 → 订单列表 → 订单详情 多页面流程。
/// 每个交互元素均设置 accessibilityIdentifier，供 RodSki 移动端自动化测试定位。
@main
struct RodskiDemoApp: App {
    var body: some Scene {
        WindowGroup {
            LoginView()
        }
    }
}

/// 订单数据模型。字段与 Android Demo 的 mock_server.py 完全一致：
/// order_id / customer / amount / status。
struct Order: Identifiable {
    var id: String { orderId }
    let orderId: String
    let customer: String
    let amount: Double
    let status: String
}

/// 本地内置订单数据（与 mobile_app/scripts/mock_server.py 的 ORDERS 对齐）。
/// 首次验收简化为本地数据，暂不调后端。
enum DemoData {
    static let orders: [Order] = [
        Order(orderId: "SO-20260601-001", customer: "张三", amount: 1299.00, status: "已发货"),
        Order(orderId: "SO-20260601-002", customer: "李四", amount: 458.50, status: "待付款"),
        Order(orderId: "SO-20260601-003", customer: "王五", amount: 8800.00, status: "已完成"),
    ]

    /// 有效账号：demo / demo123（与 Android Demo 一致）。
    static let validUsername = "demo"
    static let validPassword = "demo123"
}
