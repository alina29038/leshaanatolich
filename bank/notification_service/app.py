import pika
import json


def send_push_notification(user_id, message):
    print(f"Push notification to user {user_id}: {message}")


connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()


channel.queue_declare(queue='notifications_queue', durable=True)


def callback(ch, method, properties, body):
    notification = json.loads(body)
    user_id = notification['user_id']
    message = notification['message']

    send_push_notification(user_id, message)

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='notifications_queue', on_message_callback=callback)

print("сервис уведомлений запущен...")
channel.start_consuming()
