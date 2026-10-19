import SwiftUI

/// 主页。对应 Android `.HomeActivity`。
///
/// accessibility-id 对齐：
///   welcome_text / order_list_button
struct HomeView: View {
    let username: String

    var body: some View {
        VStack(spacing: 30) {
            Text("欢迎，\(username)")
                .font(.title2)
                .accessibilityIdentifier("welcome_text")

            NavigationLink(destination: OrderListView()) {
                Text("订单列表")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
            .accessibilityIdentifier("order_list_button")

            Spacer()
        }
        .padding()
        .navigationTitle("主页")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        HomeView(username: "demo")
    }
}
