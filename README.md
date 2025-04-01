# queue_send_email

Storage queue-triggered Azure Function to send email via external webhook.

## Required Environment Variables
- SOURCE_QUEUE: The name of the Azure Queue Storage queue to listen to.
- WEBHOOK_URL: The URL of the webhook to send the email data to.
- WEBHOOK_USER: The username for basic authentication to the webhook.
- WEBHOOK_PASS: The password for basic authentication to the webhook.

## Incoming Queue Message Format

```json5
{
  "subject": "string",  // email subject
  "header": "string",  // email intro text
  "footer": "string",  // email footer text
  "caption": "string",  // table caption
  "columns": [  // list of table column names
    "string",
    "string2",
    "..."
  ],
  "rows": [  // list of table rows (dictionaries of key-value pairs; keys should match column names)
    {
      "string": "string",
      "string2": "string",
      "...": "..."
    },
    {
      "string": "string",
      "string2": "string",
      "...": "..."
    }
  ],
  "recipents": "user@example.com, user2@example.com",  // comma and space separated string of email addresses
  "sender": "user3@example.com"  // sender email address
}
```