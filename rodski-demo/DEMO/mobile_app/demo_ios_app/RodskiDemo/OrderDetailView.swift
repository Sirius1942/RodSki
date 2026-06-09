import SwiftUI

/// 订单详情页。对应 Android `.OrderDetailActivity`。
///
/// accessibility-id 对齐：
///   order_no / customer_name / amount / status
struct OrderDetailView: View {
    let order: Order

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            row(title: "订单号", value: order.orderId, id: "order_no")
            row(title: "客户", value: order.customer, id: "customer_name")
            row(title: "金额", value: String(format: "%.2f", order.amount), id: "amount")
            row(title: "状态", value: order.status, id: "status")
            Spacer()
        }
        .padding()
        .navigationTitle("订单详情")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func row(title: String, value: String, id: String) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .frame(width: 80, alignment: .leading)
            Text(value)
                .font(.body)
                .accessibilityIdentifier(id)
            Spacer()
        }
    }
}

#Preview {
    NavigationStack {
        OrderDetailView(order: DemoData.orders[0])
    }
}
