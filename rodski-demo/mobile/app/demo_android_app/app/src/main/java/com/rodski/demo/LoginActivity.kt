package com.rodski.demo

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val usernameField = findViewById<EditText>(R.id.username)
        val passwordField = findViewById<EditText>(R.id.password)
        val loginBtn = findViewById<Button>(R.id.loginBtn)
        val errorMsg = findViewById<TextView>(R.id.errorMsg)

        loginBtn.setOnClickListener {
            val username = usernameField.text.toString()
            val password = passwordField.text.toString()
            errorMsg.visibility = View.GONE

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val response = RetrofitClient.getInstance().login(LoginRequest(username, password))
                    withContext(Dispatchers.Main) {
                        if (response.isSuccessful && response.body()?.success == true) {
                            val intent = Intent(this@LoginActivity, HomeActivity::class.java)
                            intent.putExtra("username", username)
                            startActivity(intent)
                        } else {
                            errorMsg.text = response.body()?.message ?: "用户名或密码错误"
                            errorMsg.visibility = View.VISIBLE
                        }
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        errorMsg.text = "网络错误: ${e.message}"
                        errorMsg.visibility = View.VISIBLE
                    }
                }
            }
        }
    }
}
