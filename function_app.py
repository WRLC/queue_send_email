"""
Azure Function to process messages from an Azure Queue Storage
"""
import json
import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# noinspection PyPackageRequirements
import azure.functions as func
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
import requests  # type:ignore[import-untyped]
from requests import Response  # type:ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type:ignore[import-untyped]

app: func.FunctionApp = func.FunctionApp()

if not os.getenv('SOURCE_QUEUE'):
    raise ValueError('SOURCE_QUEUE not set')  # Exit if the source queue is not set


class Email:
    """
    Email object
    """
    def __init__(self, subject: str, body: str, recipients: str, sender: str,) -> None:
        """
        Email object

        :param subject: str
        :param body: str
        :param recipients: str
        :param sender: str
        :return: None
        """
        self.subject: str = subject
        self.body: str = body
        self.recipients: str = recipients
        self.sender: str = sender

    def send(self) -> None:
        """
        Send the email to webhook

        :return: None
        """
        if os.getenv('SMTP_SERVER'):  # If the SMTP server is set
            self.send_smtp()  # Send the email using SMTP

        elif os.getenv('WEBHOOK_URL'):  # If the webhook URL is set
            self.send_webhook()  # Send the email using webhook
        else:  # If neither SMTP server nor webhook URL is set
            raise ValueError('No SMTP server or webhook URL set')  # Raise error

    def send_smtp(self) -> None:
        """
        Send the email using SMTP
        :return:
        """

        server: str = os.getenv('SMTP_SERVER', '')
        port: int = int(os.getenv('SMTP_PORT', '587'))
        username: str = os.getenv('SMTP_USERNAME', '')
        password: str = os.getenv('SMTP_PASSWORD', '')

        if not all([server, port, username, password]):
            raise ValueError('SMTP configuration incomplete')

        msg: MIMEMultipart = MIMEMultipart('alternative')
        msg['Subject'] = self.subject
        msg['From'] = self.sender
        msg['To'] = self.recipients

        html_part: MIMEText = MIMEText(self.body, 'html')
        msg.attach(html_part)

        try:
            smtp: smtplib.SMTP = smtplib.SMTP(server, port)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(self.sender, self.recipients.split(','), msg.as_string())
            smtp.quit()
            logging.info('Email sent via SMTP to %s', self.recipients)
        except Exception as e:
            logging.error('SMTP Error: %s', str(e))
            raise

    def send_webhook(self) -> None:
        """
        Send the email using webhook
        :return:
        """
        if not os.getenv('WEBHOOK_USER') or not os.getenv('WEBHOOK_PASS'):
            raise ValueError('WEBHOOK_USER and WEBHOOK_PASS must be set')

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


def render_template(template_name: str, **kwargs) -> str:
    """
    Render a Jinja template with the variables passed in

    :param template_name: str
    :param kwargs: dict
    :return: str
    """
    env: Environment = Environment(  # create the environment
        loader=FileSystemLoader('templates'),  # load the templates from the templates directory
        autoescape=select_autoescape(['html', 'xml'])  # autoescape html and xml
    )

    template: Template = env.get_template(template_name)  # get the template

    body: str = template.render(**kwargs)  # render the template with the variables passed in

    return body
