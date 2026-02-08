def send_invoice_email(to_email: str, subject: str, body: str, attachment_bytes: bytes) -> bool:
    """
    Mock email sender.
    In a real app, this would use SMTP or an API like SendGrid/SES.
    """
    print(f"--- [MOCK EMAIL SERVICE] ---")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"Attachment Size: {len(attachment_bytes)} bytes")
    print("----------------------------")
    return True
