package com.rodski.demoapp;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String DEMO_PHONE = "13800000000";
    private static final String DEMO_PASSWORD = "demo123";

    private LinearLayout root;
    private EditText phoneInput;
    private EditText passwordInput;
    private TextView errorText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showLogin();
    }

    private void showLogin() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        int padding = dp(24);
        root.setPadding(padding, padding, padding, padding);

        TextView title = new TextView(this);
        title.setText("RodSki Mobile Demo");
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);
        root.addView(title, fullWidth());

        phoneInput = new EditText(this);
        phoneInput.setId(R.id.phoneInput);
        phoneInput.setHint("手机号");
        phoneInput.setSingleLine(true);
        phoneInput.setInputType(InputType.TYPE_CLASS_PHONE);
        root.addView(phoneInput, fullWidth());

        passwordInput = new EditText(this);
        passwordInput.setId(R.id.passwordInput);
        passwordInput.setHint("密码");
        passwordInput.setSingleLine(true);
        passwordInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(passwordInput, fullWidth());

        Button loginButton = new Button(this);
        loginButton.setId(R.id.loginButton);
        loginButton.setText("登录");
        loginButton.setOnClickListener(view -> handleLogin());
        root.addView(loginButton, fullWidth());

        errorText = new TextView(this);
        errorText.setId(R.id.errorText);
        errorText.setText("");
        errorText.setGravity(Gravity.CENTER);
        root.addView(errorText, fullWidth());

        setContentView(root);
    }

    private void handleLogin() {
        String phone = phoneInput.getText().toString().trim();
        String password = passwordInput.getText().toString();
        if (DEMO_PHONE.equals(phone) && DEMO_PASSWORD.equals(password)) {
            showHome(phone);
            return;
        }
        errorText.setText("手机号或密码错误");
    }

    private void showHome(String phone) {
        LinearLayout home = new LinearLayout(this);
        home.setOrientation(LinearLayout.VERTICAL);
        home.setGravity(Gravity.CENTER_HORIZONTAL);
        int padding = dp(24);
        home.setPadding(padding, padding, padding, padding);

        TextView welcome = new TextView(this);
        welcome.setId(R.id.welcomeText);
        welcome.setText("欢迎使用 RodSki Mobile Demo");
        welcome.setTextSize(20);
        welcome.setGravity(Gravity.CENTER);
        home.addView(welcome, fullWidth());

        TextView signedInPhone = new TextView(this);
        signedInPhone.setId(R.id.signedInPhone);
        signedInPhone.setText(phone);
        signedInPhone.setTextSize(18);
        signedInPhone.setGravity(Gravity.CENTER);
        home.addView(signedInPhone, fullWidth());

        setContentView(home);
    }

    private LinearLayout.LayoutParams fullWidth() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, dp(8), 0, dp(8));
        return params;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
