from fastapi import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
import requests, time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost.3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

redis = get_redis_connection(
    host="redis-10606.c290.ap-northeast-1-2.ec2.cloud.redislabs.com",
    port="10606",
    password="gXWQqeVCLiQ3kEz5rWzYNIBybD9TBrTI",
    decode_responses=True
)


class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str  # pending, completed, refunded, etc

    class Meta:
        database = redis


@app.get("/orders/{pk}")
def get(pk: str):
    return Order.get(pk)


@app.post("/orders")
async def create(request: Request, background_task: BackgroundTasks):
    body = await request.json()  # id, quantity
    req = requests.get(f'http://localhost:8000/products/{body["id"]}')  # access data from another port(透過打api到其他地方)
    product = req.json()  # change data into json file

    order = Order(
        product_id=body['id'],
        price=product['price'],
        fee=0.2*product["price"],  # fee defaulted to 20% of price
        total=1.2*product["price"],
        quantity=body['quantity'],
        status='pending'
    )
    order.save()
    background_task.add_task(order_completed, order)
    return order


def order_completed(order: Order):
    time.sleep(5)
    order.status="completed"
    order.save()
    redis.xadd("order_completed", order.dict(), "*")  # sending this order to redis stream