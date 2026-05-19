package com.rodski.demo

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class HomeActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        val username = intent.getStringExtra("username") ?: "用户"
        findViewById<TextView>(R.id.welcomeText).text = "欢迎，$username"
        findViewById<Button>(R.id.orderListBtn).setOnClickListener {
            startActivity(Intent(this, OrderListActivity::class.java))
        }
    }
}
