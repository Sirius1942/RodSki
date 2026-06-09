import SwiftUI

/// 订单列表页。对应 Android `.OrderListActivity`。
///
/// accessibility-id 对齐：
///   order_list（列表容器）/ order_item（列表项）
struct OrderListView: View {
    private let orders = DemoData.orders

    var body: some View {
        List(orders) { order in
            NavigationLink(destination: OrderDetailView(order: order)) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(order.orderId)
                        .font(.headline)
                    Text("\(order.customer)  ¥\(String(format: "%.2f", order.amount))  \(order.status)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .accessibilityIdentifier("order_item")
        }
        .accessibilityIdentifier("order_list")
        .navigationTitle("订单列表")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        OrderListView()
    }
}
