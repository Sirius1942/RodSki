import json
import random

# 生成测试数据
data = {
    "order_id": f"ORD{random.randint(1000, 9999)}",
    "amount": random.randint(100, 1000)
}

print(json.dumps(data))
