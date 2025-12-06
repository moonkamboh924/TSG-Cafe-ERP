"""
Verification Code Service
Handles sending and validating verification codes via Email and SMS
Supports multiple SMS providers: MSG91, TextLocal, Fast2SMS
"""
import secrets
import string
import requests
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
from ..extensions import mail, cache


class VerificationService:
    """Service for managing verification codes"""
    
    # Code expiration time (3 minutes)
    CODE_EXPIRATION_MINUTES = 3
    
    @staticmethod
    def generate_code(length=6):
        """Generate a random numeric verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def _get_cache_key(identifier, code_type):
        """Generate cache key for storing verification codes"""
        return f"verification:{code_type}:{identifier}"
    
    @staticmethod
    def send_login_notification(user):
        """
        Send login notification email to business owner or system administrator
        
        Args:
            user: User object who logged in
            
        Returns:
            dict: Result with success status
        """
        try:
            from datetime import datetime, timezone
            from ..models import SystemSetting
            import socket
            
            # Get business name (system admins don't have business_id)
            if user.business_id:
                business_name = SystemSetting.get_setting('restaurant_name', 'My Business', business_id=user.business_id)
            else:
                # System administrator - use system name
                business_name = 'TSG Cafe ERP System'
            
            # Get login details
            login_time = datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p UTC')
            
            # Try to get IP address (may not be available in all contexts)
            try:
                ip_address = socket.gethostbyname(socket.gethostname())
            except:
                ip_address = 'Unknown'
            
            # Prepare email
            subject = f"🔐 New Login Alert - {business_name}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 10px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 20px 15px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ background: #f8f9fa; padding: 20px 15px; }}
                    .info-box {{ background: white; border-left: 4px solid #667eea; 
                                padding: 12px; margin: 15px 0; border-radius: 5px; }}
                    .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; 
                               border-bottom: 1px solid #e9ecef; flex-wrap: wrap; }}
                    .info-label {{ font-weight: bold; color: #666; font-size: 14px; }}
                    .info-value {{ color: #333; font-size: 14px; word-break: break-word; }}
                    .alert {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                             padding: 12px; margin: 15px 0; border-radius: 5px; font-size: 14px; }}
                    .footer {{ text-align: center; padding: 15px 10px; color: #666; font-size: 11px; }}
                    
                    /* Mobile responsive */
                    @media only screen and (max-width: 600px) {{
                        .container {{ padding: 5px; }}
                        .header {{ padding: 15px 10px; border-radius: 5px 5px 0 0; }}
                        .header h1 {{ font-size: 20px; }}
                        .content {{ padding: 15px 10px; }}
                        .info-box {{ padding: 10px; margin: 10px 0; }}
                        .info-row {{ flex-direction: column; padding: 5px 0; }}
                        .info-label, .info-value {{ font-size: 13px; }}
                        .info-value {{ margin-top: 3px; }}
                        .alert {{ padding: 10px; margin: 10px 0; font-size: 13px; }}
                        .footer {{ padding: 12px 8px; font-size: 10px; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Login Notification</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user.full_name}</strong>,</p>
                        <p>We detected a new login to your <strong>{business_name}</strong> account.</p>
                        
                        <div class="info-box">
                            <div class="info-row">
                                <span class="info-label">👤 Account:</span>
                                <span class="info-value">{user.email}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">⏰ Time:</span>
                                <span class="info-value">{login_time}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">🌐 IP Address:</span>
                                <span class="info-value">{ip_address}</span>
                            </div>
                            <div class="info-row" style="border-bottom: none;">
                                <span class="info-label">💼 Role:</span>
                                <span class="info-value">{user.role.title()}</span>
                            </div>
                        </div>
                        
                        <div class="alert">
                            <strong>⚠️ Security Notice:</strong><br>
                            If this wasn't you, please secure your account immediately by changing your password 
                            and contacting support.
                        </div>
                        
                        <p>This notification helps protect your account from unauthorized access.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2025 Trisync Global. All rights reserved.</p>
                        <p>This is an automated security notification.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version for email clients that don't support HTML
            text_body = f"""
            🔐 Login Notification
            
            Hello {user.full_name},
            
            We detected a new login to your {business_name} account.
            
            Login Details:
            - Account: {user.email}
            - Time: {login_time}
            - IP Address: {ip_address}
            - Role: {user.role.title()}
            
            ⚠️ Security Notice:
            If this wasn't you, please secure your account immediately by changing your password 
            and contacting support.
            
            This notification helps protect your account from unauthorized access.
            
            © 2025 Trisync Global. All rights reserved.
            This is an automated security notification.
            """
            
            # Send email with display name (same as verification emails)
            sender_email = current_app.config.get('MAIL_USERNAME')
            sender_name = 'TSG Cafe ERP'
            
            msg = Message(
                subject=subject,
                sender=(sender_name, sender_email),  # Display name and email
                recipients=[user.email],
                body=text_body,
                html=html_body
            )
            
            mail.send(msg)
            
            return {
                'success': True,
                'message': 'Login notification sent successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f'Failed to send login notification: {str(e)}')
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def send_email_code(email, business_name=None):
        """
        Generate and send verification code via email
        
        Args:
            email (str): Email address to send code to
            business_name (str): Business name for personalization
            
        Returns:
            dict: Result with success status and code (for testing)
        """
        try:
            # Generate 6-digit code
            code = VerificationService.generate_code()
            
            # Store code in cache with expiration
            cache_key = VerificationService._get_cache_key(email, 'email')
            cache.set(cache_key, code, timeout=VerificationService.CODE_EXPIRATION_MINUTES * 60)
            
            # Prepare email
            subject = f"Verification Code - {business_name or 'TSG Cafe ERP'}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 10px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 20px 15px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ background: #f8f9fa; padding: 20px 15px; }}
                    .code-box {{ background: white; border: 2px dashed #667eea; padding: 20px 15px; 
                                text-align: center; font-size: 32px; font-weight: bold; 
                                letter-spacing: 8px; color: #667eea; margin: 20px 0; 
                                border-radius: 8px; word-break: break-all; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                               padding: 12px; margin: 15px 0; font-size: 14px; }}
                    .footer {{ text-align: center; padding: 15px 10px; color: #666; font-size: 11px; }}
                    
                    /* Mobile responsive */
                    @media only screen and (max-width: 600px) {{
                        .container {{ padding: 5px; }}
                        .header {{ padding: 15px 10px; border-radius: 5px 5px 0 0; }}
                        .header h1 {{ font-size: 20px; }}
                        .content {{ padding: 15px 10px; }}
                        .code-box {{ font-size: 28px; letter-spacing: 6px; padding: 15px 10px; margin: 15px 0; }}
                        .warning {{ padding: 10px; margin: 10px 0; font-size: 13px; }}
                        .footer {{ padding: 12px 8px; font-size: 10px; }}
                        body, p {{ font-size: 14px; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Email Verification</h1>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p>Thank you for registering with <strong>{business_name or 'TSG Cafe ERP'}</strong>!</p>
                        <p>Your email verification code is:</p>
                        
                        <div class="code-box">{code}</div>
                        
                        <div class="warning">
                            <strong>⏰ Important:</strong> This code will expire in 
                            <strong>{VerificationService.CODE_EXPIRATION_MINUTES} minutes</strong>.
                        </div>
                        
                        <p>If you didn't request this code, please ignore this email.</p>
                        <p>For security reasons, never share this code with anyone.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2025 Trisync Global. All rights reserved.</p>
                        <p>This is an automated message, please do not reply.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Email Verification Code
            
            Hello,
            
            Thank you for registering with {business_name or 'TSG Cafe ERP'}!
            
            Your email verification code is: {code}
            
            This code will expire in {VerificationService.CODE_EXPIRATION_MINUTES} minutes.
            
            If you didn't request this code, please ignore this email.
            
            For security reasons, never share this code with anyone.
            
            © 2025 Trisync Global. All rights reserved.
            """
            
            # Send email with display name
            sender_email = current_app.config.get('MAIL_USERNAME')
            sender_name = 'TSG Cafe ERP'
            
            msg = Message(
                subject=subject,
                sender=(sender_name, sender_email),  # Display name and email
                recipients=[email],
                body=text_body,
                html=html_body
            )
            
            mail.send(msg)
            
            return {
                'success': True,
                'message': f'Verification code sent to {email}',
                'expires_in_minutes': VerificationService.CODE_EXPIRATION_MINUTES
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to send email verification code: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }
    
    @staticmethod
    def send_sms_code(phone_number, business_name=None):
        """
        Generate and send verification code via SMS
        Supports: Twilio (recommended for Pakistan), MSG91, Fast2SMS
        
        Args:
            phone_number (str): Phone number to send SMS to (include country code)
            business_name (str): Business name for personalization
            
        Returns:
            dict: Result with success status and code (for testing)
        """
        try:
            # Generate 6-digit code
            code = VerificationService.generate_code()
            
            # Store code in cache with expiration
            cache_key = VerificationService._get_cache_key(phone_number, 'sms')
            cache.set(cache_key, code, timeout=VerificationService.CODE_EXPIRATION_MINUTES * 60)
            
            # Get SMS provider from config
            sms_provider = current_app.config.get('SMS_PROVIDER', 'TWILIO').upper()
            
            # Prepare SMS message
            message_text = f"{business_name or 'TSG Cafe ERP'} Verification\n\nYour code: {code}\n\nExpires in {VerificationService.CODE_EXPIRATION_MINUTES} minutes.\nDo not share this code."
            
            # Send SMS based on provider
            if sms_provider == 'TWILIO':
                result = VerificationService._send_twilio(phone_number, code, message_text)
            elif sms_provider == 'MSG91':
                result = VerificationService._send_msg91(phone_number, code, message_text)
            elif sms_provider == 'FAST2SMS':
                result = VerificationService._send_fast2sms(phone_number, code, message_text)
            else:
                raise ValueError(f"Unsupported SMS provider: {sms_provider}")
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Verification code sent to {phone_number}',
                    'expires_in_minutes': VerificationService.CODE_EXPIRATION_MINUTES,
                    'provider': sms_provider
                }
            else:
                return result
            
        except Exception as e:
            current_app.logger.error(f"Failed to send SMS verification code: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send SMS: {str(e)}'
            }
    
    @staticmethod
    def _send_twilio(phone_number, code, message):
        """Send SMS using Twilio (Works in Pakistan - $15 free trial)"""
        try:
            from twilio.rest import Client
            
            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
            from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
            
            if not all([account_sid, auth_token, from_number]):
                raise ValueError("Twilio credentials not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env")
            
            # Ensure phone number has country code
            if not phone_number.startswith('+'):
                # Assume Pakistan if no country code
                phone_number = f'+92{phone_number.lstrip("0")}'
            
            client = Client(account_sid, auth_token)
            
            # Send SMS
            sms_message = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            
            current_app.logger.info(f"Twilio SMS sent to {phone_number}: {sms_message.sid}")
            return {'success': True, 'sid': sms_message.sid}
            
        except Exception as e:
            current_app.logger.error(f"Twilio SMS error: {str(e)}")
            return {'success': False, 'message': f'Twilio error: {str(e)}'}
    
    @staticmethod
    def _send_msg91(phone_number, code, message):
        """Send SMS using MSG91 (Paid service - works in Pakistan)"""
        try:
            auth_key = current_app.config.get('MSG91_AUTH_KEY')
            sender_id = current_app.config.get('MSG91_SENDER_ID', 'TSGCAF')
            route = current_app.config.get('MSG91_ROUTE', '4')  # 4 = Transactional
            
            if not auth_key:
                raise ValueError("MSG91_AUTH_KEY not configured")
            
            # Clean phone number (remove + and spaces)
            clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            
            # MSG91 API URL
            url = "https://api.msg91.com/api/v5/flow/"
            
            # Using Flow API (recommended)
            payload = {
                "template_id": current_app.config.get('MSG91_TEMPLATE_ID'),
                "short_url": "0",
                "recipients": [{
                    "mobiles": clean_phone,
                    "var1": code,
                    "var2": str(VerificationService.CODE_EXPIRATION_MINUTES)
                }]
            }
            
            headers = {
                "authkey": auth_key,
                "content-type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return {'success': True, 'response': response.json()}
            else:
                return {'success': False, 'message': f'MSG91 error: {response.text}'}
                
        except Exception as e:
            return {'success': False, 'message': f'MSG91 exception: {str(e)}'}
    
    @staticmethod
    def _send_textlocal(phone_number, code, message):
        """Send SMS using TextLocal (Free: 100 SMS for testing)"""
        try:
            api_key = current_app.config.get('TEXTLOCAL_API_KEY')
            sender = current_app.config.get('TEXTLOCAL_SENDER', 'TSGCAF')
            
            if not api_key:
                raise ValueError("TEXTLOCAL_API_KEY not configured")
            
            # Clean phone number
            clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            
            # TextLocal API
            url = "https://api.textlocal.in/send/"
            
            payload = {
                'apikey': api_key,
                'numbers': clean_phone,
                'sender': sender,
                'message': message
            }
            
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            
            if result.get('status') == 'success':
                return {'success': True, 'response': result}
            else:
                return {'success': False, 'message': f'TextLocal error: {result.get("message", "Unknown error")}'}
                
        except Exception as e:
            return {'success': False, 'message': f'TextLocal exception: {str(e)}'}
    
    @staticmethod
    def _send_fast2sms(phone_number, code, message):
        """Send SMS using Fast2SMS (Free: 50 SMS/day)"""
        try:
            api_key = current_app.config.get('FAST2SMS_API_KEY')
            
            if not api_key:
                raise ValueError("FAST2SMS_API_KEY not configured")
            
            # Clean phone number (Fast2SMS works with Indian numbers)
            clean_phone = phone_number.replace('+91', '').replace('+', '').replace(' ', '').replace('-', '')
            
            # Fast2SMS API
            url = "https://www.fast2sms.com/dev/bulkV2"
            
            payload = {
                'authorization': api_key,
                'variables_values': code,
                'route': 'otp',
                'numbers': clean_phone,
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cache-Control': 'no-cache'
            }
            
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            result = response.json()
            
            if result.get('return') == True:
                return {'success': True, 'response': result}
            else:
                return {'success': False, 'message': f'Fast2SMS error: {result.get("message", "Unknown error")}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Fast2SMS exception: {str(e)}'}
    
    @staticmethod
    def verify_email_code(email, code):
        """
        Verify email verification code
        
        Args:
            email (str): Email address
            code (str): Code to verify
            
        Returns:
            dict: Result with success status
        """
        cache_key = VerificationService._get_cache_key(email, 'email')
        stored_code = cache.get(cache_key)
        
        if not stored_code:
            return {
                'success': False,
                'message': 'Code expired or not found. Please request a new code.'
            }
        
        if stored_code != code:
            return {
                'success': False,
                'message': 'Invalid verification code. Please try again.'
            }
        
        # Code is valid - remove it from cache
        cache.delete(cache_key)
        
        return {
            'success': True,
            'message': 'Email verification successful!'
        }
    
    @staticmethod
    def verify_sms_code(phone_number, code):
        """
        Verify SMS verification code
        
        Args:
            phone_number (str): Phone number
            code (str): Code to verify
            
        Returns:
            dict: Result with success status
        """
        cache_key = VerificationService._get_cache_key(phone_number, 'sms')
        stored_code = cache.get(cache_key)
        
        if not stored_code:
            return {
                'success': False,
                'message': 'Code expired or not found. Please request a new code.'
            }
        
        if stored_code != code:
            return {
                'success': False,
                'message': 'Invalid verification code. Please try again.'
            }
        
        # Code is valid - remove it from cache
        cache.delete(cache_key)
        
        return {
            'success': True,
            'message': 'Mobile verification successful!'
        }
    
    @staticmethod
    def send_both_codes(email, phone_number, business_name=None):
        """
        Send verification codes to both email and phone
        
        Args:
            email (str): Email address
            phone_number (str): Phone number
            business_name (str): Business name
            
        Returns:
            dict: Results for both email and SMS
        """
        email_result = VerificationService.send_email_code(email, business_name)
        sms_result = VerificationService.send_sms_code(phone_number, business_name)
        
        return {
            'email': email_result,
            'sms': sms_result,
            'both_sent': email_result['success'] and sms_result['success']
        }
    
    @staticmethod
    def verify_both_codes(email, phone_number, email_code, sms_code):
        """
        Verify both email and SMS codes
        
        Args:
            email (str): Email address
            phone_number (str): Phone number
            email_code (str): Email verification code
            sms_code (str): SMS verification code
            
        Returns:
            dict: Verification results
        """
        email_result = VerificationService.verify_email_code(email, email_code)
        sms_result = VerificationService.verify_sms_code(phone_number, sms_code)
        
        return {
            'email_verified': email_result['success'],
            'sms_verified': sms_result['success'],
            'both_verified': email_result['success'] and sms_result['success'],
            'email_message': email_result['message'],
            'sms_message': sms_result['message']
        }
