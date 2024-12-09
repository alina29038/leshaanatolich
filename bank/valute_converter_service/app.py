import pika
import json
import redis
import requests
from apscheduler.schedulers.background import BackgroundScheduler

r = redis.Redis(host='localhost', port=6379, db=0)

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='currency_conversion_queue')


def fetch_exchange_rates():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        rates = data['rates']

        for currency, rate in rates.items():
            r.set(currency, rate)
        print("Exchange rates updated.")
    else:
        print("Failed to fetch exchange rates.")


def on_request(ch, method, props, body):
    request_data = json.loads(body)
    currency = request_data['currency']
    amount = request_data['amount']

    rate = float(r.get(currency) or 1.0)
    amount_in_rub = amount * rate

    response = json.dumps({"amount_in_rub": amount_in_rub})

    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=response
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='currency_conversion_queue', on_message_callback=on_request)

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_exchange_rates, 'interval', hours=1)
scheduler.start()

print("обмен валют запущен...")
fetch_exchange_rates()
channel.start_consuming()
