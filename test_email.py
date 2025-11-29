"""
Test Gmail SMTP Connection
Run this to verify your Gmail credentials are working
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Your credentials
MAIL_USERNAME = "m.mamoon924@gmail.com"
MAIL_PASSWORD = "wbwieuafgwjfshid"
TEST_RECIPIENT = "m.mamoon924@gmail.com"  # Send test to yourself

def test_gmail_connection():
    print("=" * 60)
    print("Testing Gmail SMTP Connection")
    print("=" * 60)
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = TEST_RECIPIENT
        msg['Subject'] = "Test Email - TSG Cafe ERP"
        
        body = """
        This is a test email from TSG Cafe ERP.
        
        If you receive this, your Gmail SMTP is configured correctly!
        
        Your verification code is: 123456
        """
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"\n✓ Connecting to Gmail SMTP server...")
        print(f"  Server: smtp.gmail.com:587")
        print(f"  Username: {MAIL_USERNAME}")
        print(f"  Password: {'*' * len(MAIL_PASSWORD)}")
        
        # Connect to Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Show detailed output
        
        print(f"\n✓ Starting TLS encryption...")
        server.starttls()
        
        print(f"\n✓ Attempting login...")
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        
        print(f"\n✓ Sending test email to {TEST_RECIPIENT}...")
        server.send_message(msg)
        
        print(f"\n✓ Closing connection...")
        server.quit()
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Email sent successfully!")
        print("=" * 60)
        print(f"\nCheck your inbox: {TEST_RECIPIENT}")
        print("If you received the email, your configuration is correct!")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "=" * 60)
        print("❌ AUTHENTICATION ERROR")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print("\nPossible solutions:")
        print("1. Check if 2-Factor Authentication is enabled:")
        print("   https://myaccount.google.com/security")
        print("\n2. Generate a new App Password:")
        print("   https://myaccount.google.com/apppasswords")
        print("\n3. Make sure to:")
        print("   - Copy the password WITHOUT spaces")
        print("   - Use the FULL email address")
        print("   - Delete old app passwords before creating new ones")
        
        return False
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        return False

if __name__ == "__main__":
    test_gmail_connection()
