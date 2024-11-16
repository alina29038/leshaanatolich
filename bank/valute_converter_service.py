import pika
import json
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='currency_conversion_queue')

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

print("ожидание запросов...")
channel.start_consuming()
