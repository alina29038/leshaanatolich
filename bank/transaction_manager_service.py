import pika
import json
import uuid
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class TransactionRequest(BaseModel):
    sender_id: int
    initial_amount: float
    currency: str
    receiver_id: int


class CurrencyConverterClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.callback_queue = self.channel.queue_declare(queue='', exclusive=True, durable=True).method.queue
        self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)
        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def convert_currency(self, currency, amount):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        request_data = json.dumps({"currency": currency, "amount": amount})

        self.channel.basic_publish(
            exchange='',
            routing_key='currency_conversion_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=request_data
        )
        while self.response is None:
            self.connection.process_data_events()
        return self.response["amount_in_rub"]


@app.get("/", response_class=HTMLResponse)
def show_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/submit_transaction/")
def process_transaction(
        sender_id: int = Form(...),
        initial_amount: float = Form(...),
        currency: str = Form(...),
        receiver_id: int = Form(...)
):
    converter = CurrencyConverterClient()
    converted_amount = converter.convert_currency(currency, initial_amount)

    transaction_data = {
        "sender_id": sender_id,
        "initial_amount": initial_amount,
        "currency": currency,
        "receiver_id": receiver_id,
        "amount_in_rub": converted_amount
    }
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='transaction_queue', durable=True)
    channel.basic_publish(exchange='', routing_key='transaction_queue', body=json.dumps(transaction_data))
    connection.close()

    return {"status": "Transaction processed"}
