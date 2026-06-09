import SwiftUI

/// 登录页。对应 Android `.LoginActivity`。
///
/// accessibility-id 对齐：
///   username_field / password_field / login_button / error_msg
struct LoginView: View {
    @State private var username = ""
    @State private var password = ""
    @State private var errorMessage = ""
    @State private var showError = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("RodSki Demo 登录")
                    .font(.title)
                    .padding(.bottom, 20)

                TextField("用户名", text: $username)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .accessibilityIdentifier("username_field")

                SecureField("密码", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("password_field")

                // 登录成功时跳转 HomeView。
                NavigationLink(destination: HomeView(username: username), isActive: $loginSuccess) {
                    EmptyView()
                }

                Button(action: login) {
                    Text("登录")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .accessibilityIdentifier("login_button")

                if showError {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .accessibilityIdentifier("error_msg")
                }

                Spacer()
            }
            .padding()
            .navigationTitle("登录")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    @State private var loginSuccess = false

    /// 本地校验账号 demo / demo123，不调后端（简化首次验收）。
    private func login() {
        showError = false
        if username == DemoData.validUsername && password == DemoData.validPassword {
            loginSuccess = true
        } else {
            errorMessage = "用户名或密码错误"
            showError = true
        }
    }
}

#Preview {
    LoginView()
}
