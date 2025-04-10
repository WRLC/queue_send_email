# queue_send_email

Storage queue-triggered Azure Function to send email via external webhook.

## Required Environment Variables
- SOURCE_QUEUE: The name of the Azure Queue Storage queue to listen to.
- WEBHOOK_URL: The URL of the webhook to send the email data to.
- WEBHOOK_USER: The username for basic authentication to the webhook.
- WEBHOOK_PASS: The password for basic authentication to the webhook.
- DEFAULT_SENDER: The default sender email address to use if not provided in the queue message.

## Incoming Queue Message Format

```json5
{
  "subject": "string",  // email subject
  "header": "string",  // email intro text
  "footer": "string",  // email footer text
  "caption": "string",  // table caption
  "columns": {  // dictionary of table column names
    "key": "value",
    "key2": "value2",
    "...": "..."
  },
  "rows": [  // list of table rows key-value pairs (key should match a column value)
    {
      "value": "string",
      "value2": "string2",
      "...": "..."
    },
    {
      "value": "string3",
      "value2": "string4",
      "...": "..."
    }
  ],
  "recipents": "user@example.com, user2@example.com",  // comma-separated string of addresses
  "sender": "user3@example.com"  // sender email address
}
```