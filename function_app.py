"""
Azure Function to process messages from an Azure Queue Storage
"""
import json
import logging
import os
import re
# noinspection PyPackageRequirements
import azure.functions as func
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
import requests  # type:ignore[import-untyped]
from requests import Response  # type:ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type:ignore[import-untyped]

app: func.FunctionApp = func.FunctionApp()

if not os.getenv('SOURCE_QUEUE'):
    raise ValueError('SOURCE_QUEUE not set')  # Exit if the source queue is not set


# pylint: disable=too-few-public-methods
class Email:
    """
    Email object
    """
    def __init__(
            self,
            subject: str,
            body: str,
            recipients: str,
            sender: str,
    ):
        """
        Email object

        :param subject: str
        :param body: str
        :param recipients: str
        :param sender: str
        :return: None
        """
        self.subject = subject
        self.body = body
        self.recipients = recipients
        self.sender = sender

    def send(self) -> None:
        """
        Send the email to webhook

        :return: None
        """
        if not os.getenv('WEBHOOK_URL'):  # If the webhook URL is not set
            raise ValueError('WEBHOOK_URL not set')  # Exit if the webhook URL is not set

        if not os.getenv('WEBHOOK_USER') or not os.getenv('WEBHOOK_PASS'):  # If the webhook user or password is not set
            raise ValueError('WEBHOOK_USER or WEBHOOK_PASS not set')  # Exit if the webhook user or password is not set

        basic: HTTPBasicAuth = HTTPBasicAuth(os.getenv('WEBHOOK_USER'), os.getenv('WEBHOOK_PASS'))  # auth for webhook

        try:  # Try to send the email
            response: Response = requests.post(  # Send the email
                url=os.getenv('WEBHOOK_URL'),  # URL for the webhook
                json={  # JSON payload for the webhook
                    "subject": self.subject,  # subject of the email
                    "body": self.body,  # body of the email
                    "to": self.recipients,  # recipient(s)
                    "sender": self.sender  # sender
                },
                auth=basic,  # Basic auth for webhook
                timeout=30  # Timeout for the request
            )

        except requests.exceptions.RequestException as e:  # Handle exceptions
            logging.error('Error: %s', e)  # Log the error
            return

        if response.status_code != 201:  # If the response status code is not 201
            logging.error('Error %s: %s', response.status_code, response.text)  # Log the error
            return

        logging.info('Email sent: %s', response.text)  # Log the success message


@app.queue_trigger(
    arg_name="azqueue",
    queue_name=os.getenv('SOURCE_QUEUE'),  # type:ignore[arg-type]
    connection="AzureWebJobsStorage"
)
def queuesendemail(azqueue: func.QueueMessage) -> None:
    """
    Process a message from the Azure Queue Storage.

    :param azqueue:
    :return: None
    """
    message: str = azqueue.get_body().decode()  # Decode the message body

    email: Email | None = construct_email(json.loads(message))  # Construct the email object
    if not email:  # If the email object is None
        return  # Exit if the email object is None

    email.send()  # Send the email


def construct_email(message) -> Email:
    """
    Construct the email object

    :param message: str
    :return: Email object
    """
    if not message['recipients']:  # If no recipients
        raise ValueError('No recipients')  # Raise error

    if not message['sender']:  # If no sender

        if not os.getenv('DEFAULT_SENDER'):  # If no default sender set
            raise ValueError('No sender')  # Raise error

        message['sender'] = os.getenv('DEFAULT_SENDER')  # Fallback to default sender

    body: str = render_template(  # Build email body
        'email.html',  # template
        header=message['header'],  # header text
        caption=message['caption'],  # table caption
        columns=message['columns'],  # table columns
        rows=message['rows'],  # table rows
        footer=message['footer'],  # footer text
    )

    email: Email = Email(  # Create the email object
        subject=message['subject'] if message['subject'] else '',  # subject
        body=body,  # body
        recipients=re.sub(r",(\S)", r", \1", message['recipients']),  # recipients
        sender=message['sender']  # sender
    )

    return email


def render_template(template, **kwargs) -> str:
    """
    Render a Jinja template with the variables passed in

    :param template: str
    :param kwargs: dict
    :return: str
    """
    env: Environment = Environment(  # create the environment
        loader=FileSystemLoader('templates'),  # load the templates from the templates directory
        autoescape=select_autoescape(['html', 'xml'])  # autoescape html and xml
    )

    template: Template = env.get_template(template)  # get the template

    body: str = template.render(**kwargs)  # render the template with the variables passed in

    return body
