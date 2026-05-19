package com.rodski.demo

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class OrderListActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_order_list)

        val recyclerView = findViewById<RecyclerView>(R.id.orderList)
        recyclerView.layoutManager = LinearLayoutManager(this)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val response = RetrofitClient.getInstance().getOrders()
                withContext(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        val orders = response.body()?.data ?: emptyList()
                        recyclerView.adapter = OrderAdapter(orders) { order ->
                            val intent = Intent(this@OrderListActivity, OrderDetailActivity::class.java)
                            intent.putExtra("order_id", order.order_id)
                            intent.putExtra("customer", order.customer)
                            intent.putExtra("amount", order.amount.toString())
                            intent.putExtra("status", order.status)
                            startActivity(intent)
                        }
                    }
                }
            } catch (e: Exception) {
                // 网络错误处理
            }
        }
    }
}
