package com.rodski.demo

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class OrderDetailActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_order_detail)

        findViewById<TextView>(R.id.orderNo).text = intent.getStringExtra("order_id") ?: ""
        findViewById<TextView>(R.id.customerName).text = intent.getStringExtra("customer") ?: ""
        findViewById<TextView>(R.id.amount).text = intent.getStringExtra("amount") ?: ""
        findViewById<TextView>(R.id.status).text = intent.getStringExtra("status") ?: ""
    }
}
