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
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; }}
                    .code-box {{ background: white; border: 2px dashed #667eea; padding: 20px; 
                                text-align: center; font-size: 32px; font-weight: bold; 
                                letter-spacing: 8px; color: #667eea; margin: 20px 0; 
                                border-radius: 8px; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                               padding: 15px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
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
