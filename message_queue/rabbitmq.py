import pika
import umsgpack
import logging
import os

from .exceptions import (
    ConnectionNotOpenedError, ChannelUndefinedError,
    WorkerExitError, ConnectionIsClosedError, CallBackError)

event_id={ "request_id":"", "event_id":""}

def catch_error(func):
    """Catch errors of rabbitmq then reconnect"""

    try:
        import pika.exceptions
        connect_exceptions = (
            pika.exceptions.ConnectionClosed,
            pika.exceptions.AMQPConnectionError,
        )
    except ImportError:
        connect_exceptions = ()

    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except connect_exceptions as e:
            logging.error('RabbitMQ error: %r, reconnect.', e, extra=event_id)
            self.reconnect()
            return func(self, *args, **kwargs)
    return wrap


LOGGER = logging.getLogger(__name__)

APPLICATION_ID="marketpalce_process_manager"
DEFAULT_DELIVERY = 2
CONTENT_TYPE="application/json"

class RabbitMqQueue:


    def __init__(self, rabbit_url):
        """Create a new instance of Connection Handler by using the given
        parameters to connect to RabbitMQ which is on environment variable
        """
        self._connection = None
        self.parameters = None
        self.init_connection(rabbit_url)

    def init_connection(self, url, timeout=86400):
        # TODO: add ssl certification
        """Setup the publisher object, passing in the host, port, user id and
        the password to create a parameters objects to connect to RabbitMQ.

        :param str url: url for RabbitMQ server
        :param int timeout: Timeout for handling the connection.
            By default, it's 0.25 seconds.
            It's not recommended to keep it to 0.25. So, we change it to 86400 sec that is 1 day.
        """
        self.parameters = pika.URLParameters(url)
        # self.parameters.heartbeat = 0
        self.parameters.socket_timeout = timeout
        # print(self.parameters,'-------<<<<')
        self._connection = pika.BlockingConnection(self.parameters)
        self._publish_channel = self.open()
        self._consume_channel = self.open()

    def reconnect(self):
        self._connection = pika.BlockingConnection(self.parameters)
        self._publish_channel = self.open()
        self._consume_channel = self.open()

    def close_connection(self):
        self._connection.close()

    def get_current_connection(self):
        return self._connection

    def open(self):
        if self._connection is None:
            LOGGER.error('The connection is not opened', extra=event_id)
            raise ConnectionNotOpenedError('The connection is not opened')

        if self._connection.is_closed:
            LOGGER.error('The connection is closed', extra=event_id)
            raise ConnectionIsClosedError('The connection is closed')

        return self._connection.channel()

    def close(self):
        LOGGER.info('The channel will close in a few time')
        self._publish_channel.close()
        self._consume_channel.close()

    def stop(self):
        try:
            self.close()
        except Exception as e:
            LOGGER.error(e)
        finally:
            self.close_connection()

    @catch_error
    def send_message(self, exchange, queue, message):
        properties = pika.BasicProperties(app_id=APPLICATION_ID,
                                          content_type=CONTENT_TYPE,
                                          delivery_mode=DEFAULT_DELIVERY)
                                          
        serialized_message = umsgpack.packb(message)

        self._publish_channel.basic_publish(
            exchange=exchange, routing_key=queue,
            body=serialized_message, properties=properties)
        LOGGER.info('message was published successfully into RabbitMQ')

    def run(self, queue, callback):
        self._on_message_callback = callback
        LOGGER.info('Consuming message on queue : %s', queue)

        try:
            """The queue can be non exist on rabbitmq, so ChannelClosed exception
            is handled by RabbitMQ and then the TCP connection is closed.
            Re-implement this if others worker can be launch and handle the
            Exception.
            """
            self.open()
            self.add_on_cancel_callback()
            self._consume_channel.basic_qos(prefetch_count=1)
            self._consume_channel.basic_consume( queue, self.on_message)
            LOGGER.info(' [*] Waiting for messages. To exit press CTRL+C')
            self._consume_channel.start_consuming()
        except Exception as e:
            LOGGER.info('The Worker will be exit after CTRL+C signal')
        finally:
            self.close()

    def on_message(self, channel, method, properties, body):
        try:
            # TODO: Handle here a dead letter queue after deciding
            # TODO: the next step of the received message
            # decoded_message = body.decode()
            self._on_message_callback(channel, method, properties, body)
        except Exception as exception_info:
            print(exception_info)
            # TODO: handle dead letter
            # LOGGER.error(
            #     'Exception {exception} occurred when trying to decode the data'
            #     'received RabbitMQ. So the message content will be put on '
            #     'queue dead letter. Here are the content of the message : '
            #     '{content}'.format(exception=exception_info, content=body))

    def acknowledge_message(self, delivery_tag):
        LOGGER.info('Acknowledging message %s', delivery_tag)
        self._consume_channel.basic_ack(delivery_tag)

    def add_on_cancel_callback(self):
        LOGGER.info('Adding consumer cancellation callback')
        self._consume_channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._consume_channel:
            self.close()