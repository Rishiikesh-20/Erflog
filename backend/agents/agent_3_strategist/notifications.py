# backend/agents/agent_3_strategist/notifications.py

"""
Agent 3: Daily Email Notification Service

Sends personalized daily digest emails to users with:
- Top 2 jobs (LLM-curated)
- Top 2 hackathons (LLM-curated)
- Top 2 news articles (LLM-curated)

Uses SMTP for email delivery and Gemini LLM for content curation.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Optional
from datetime import datetime, timezone
from supabase import create_client
from google import genai
from dotenv import load_dotenv
import json

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Notifications] - %(levelname)s - %(message)s')
logger = logging.getLogger("Notifications")

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def generate_email_html(user_name: str, jobs: list, hackathons: list, news: list) -> str:
    """
    Generate a beautiful, mobile-responsive HTML email template for daily digest.
    """
    # Calculate counts and empty states
    jobs_count = len(jobs)
    hackathons_count = len(hackathons)
    news_count = len(news)
    
    jobs_empty_display = "none" if jobs else "block"
    hackathons_empty_display = "none" if hackathons else "block"
    news_empty_display = "none" if news else "block"

    # Format jobs section
    jobs_html = ""
    for job in jobs[:2]:
        score = int(job.get("score", 0) * 100) if isinstance(job.get("score"), float) else job.get("score", 0)
        summary = (job.get('summary', '') or '')[:100]
        jobs_html += f"""
        <tr>
            <td style="padding: 0 0 16px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                    <tr>
                        <td style="padding: 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background: linear-gradient(135deg, #D95D39 0%, #e06b4a 100%); color: white; padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;">{score}% MATCH</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 14px 0 8px 0;">
                                        <h3 style="margin: 0; color: #1a1a1a; font-size: 18px; font-weight: 700; line-height: 1.3;">{job.get('title', 'Job Opportunity')}</h3>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0 0 12px 0;">
                                        <p style="margin: 0; color: #666666; font-size: 14px;">🏢 {job.get('company', 'Company')} {f"• 📍 {job.get('location')}" if job.get('location') else ""}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0 0 16px 0;">
                                        <p style="margin: 0; color: #888888; font-size: 14px; line-height: 1.5;">{summary}...</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        <a href="{job.get('link', '#')}" style="display: inline-block; background: #D95D39; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px;">View Job →</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    # Format hackathons section
    hackathons_html = ""
    for hack in hackathons[:2]:
        summary = (hack.get('summary', '') or '')[:100]
        hackathons_html += f"""
        <tr>
            <td style="padding: 0 0 16px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(135deg, #f0f4ff 0%, #e8f0ff 100%); border-radius: 16px; border: 1px solid #d4e0ff; overflow: hidden;">
                    <tr>
                        <td style="padding: 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 0 0 12px 0;">
                                        <span style="font-size: 28px;">🏆</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0 0 8px 0;">
                                        <h3 style="margin: 0; color: #1a1a1a; font-size: 18px; font-weight: 700; line-height: 1.3;">{hack.get('title', 'Hackathon')}</h3>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0 0 12px 0;">
                                        <p style="margin: 0; color: #5b6ad0; font-size: 14px; font-weight: 500;">{hack.get('company', 'Organizer')}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0 0 16px 0;">
                                        <p style="margin: 0; color: #666666; font-size: 14px; line-height: 1.5;">{summary}...</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        <a href="{hack.get('link', '#')}" style="display: inline-block; background: #5b6ad0; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px;">Register Now →</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    # Format news section
    news_html = ""
    for article in news[:2]:
        summary = (article.get('summary', '') or '')[:80]
        news_html += f"""
        <tr>
            <td style="padding: 0 0 12px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-radius: 12px; border: 1px solid #eeeeee;">
                    <tr>
                        <td style="padding: 16px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 0 0 8px 0;">
                                        <p style="margin: 0; color: #1a1a1a; font-size: 15px; font-weight: 600; line-height: 1.4;">📰 {article.get('title', 'News')}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        <p style="margin: 0; color: #888888; font-size: 13px; line-height: 1.5;">{summary}...</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    # Full email template - mobile-first, table-based for compatibility
    html = f"""
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
    <title>Your Daily Career Digest - Erflog</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        * {{ box-sizing: border-box; }}
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }}
        
        @media only screen and (max-width: 600px) {{
            .mobile-padding {{ padding-left: 16px !important; padding-right: 16px !important; }}
            .mobile-full-width {{ width: 100% !important; }}
            .mobile-text-center {{ text-align: center !important; }}
            .mobile-font-large {{ font-size: 28px !important; }}
            .mobile-font-medium {{ font-size: 16px !important; }}
            .mobile-hide {{ display: none !important; }}
            .mobile-card {{ padding: 16px !important; }}
        }}
        
        @media only screen and (min-width: 601px) {{
            .desktop-only {{ display: block !important; }}
        }}
        
        .gradient-bg {{
            background: linear-gradient(135deg, #D95D39 0%, #F18F01 50%, #c54d2d 100%);
        }}
        
        .card-hover:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(217, 93, 57, 0.15);
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background: linear-gradient(180deg, #f5f7fa 0%, #e8ecf1 100%); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    
    <!-- Preheader Text -->
    <div style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">
        Your personalized career opportunities await! Discover curated jobs, hackathons, and industry insights.
    </div>
    
    <!-- Wrapper -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(180deg, #f5f7fa 0%, #e8ecf1 100%);">
        <tr>
            <td align="center" style="padding: 32px 16px;">
                
                <!-- Main Container -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 640px; box-shadow: 0 20px 60px rgba(0,0,0,0.12);" class="mobile-full-width">
                    
                    <!-- Decorative Top Bar -->
                    <tr>
                        <td style="background: linear-gradient(90deg, #D95D39, #F18F01, #D95D39); height: 6px; border-radius: 20px 20px 0 0;"></td>
                    </tr>
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #D95D39 0%, #F18F01 50%, #c54d2d 100%); padding: 48px 32px; text-align: center; position: relative;">
                            <!-- Animated Background Pattern -->
                            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.1; background-image: radial-gradient(circle, white 1px, transparent 1px); background-size: 20px 20px;"></div>
                            
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="position: relative; z-index: 1;">
                                        <div style="display: inline-block; background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); border-radius: 20px; padding: 16px 28px; margin-bottom: 16px;">
                                            <h1 style="margin: 0; color: white; font-size: 42px; font-weight: 900; letter-spacing: -1px; text-shadow: 0 2px 12px rgba(0,0,0,0.2);" class="mobile-font-large">🚀 Erflog</h1>
                                        </div>
                                        <p style="margin: 8px 0 20px 0; color: rgba(255,255,255,0.95); font-size: 17px; font-weight: 600; letter-spacing: 0.5px;">AI-Powered Career Platform</p>
                                        <div style="margin-top: 20px;">
                                            <a href="https://erflog.vercel.app" style="display: inline-block; background: white; color: #D95D39; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: 700; font-size: 14px; letter-spacing: 0.5px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); transition: transform 0.2s;">
                                                ✨ Visit Dashboard
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="background: #ffffff; padding: 40px 32px;" class="mobile-padding">
                            
                            <!-- Greeting Section -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 0 0 32px 0;">
                                        <div style="background: linear-gradient(135deg, #FFF5F0 0%, #FFE8E0 100%); border-left: 5px solid #D95D39; border-radius: 12px; padding: 24px;">
                                            <h2 style="margin: 0 0 8px 0; color: #1a1a1a; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;" class="mobile-font-medium">Hello, {user_name}! 👋</h2>
                                            <p style="margin: 0; color: #555555; font-size: 16px; line-height: 1.7;">Your personalized career digest is ready! We've curated the best opportunities and insights tailored specifically for your career journey.</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Jobs Section -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td>
                                        <div style="display: flex; align-items: center; margin-bottom: 20px;">
                                            <div style="background: linear-gradient(135deg, #4A90E2, #357ABD); width: 48px; height: 48px; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; margin-right: 14px; box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);">
                                                <span style="font-size: 24px;">💼</span>
                                            </div>
                                            <h3 style="margin: 0; color: #1a1a1a; font-size: 22px; font-weight: 800; letter-spacing: -0.3px;">Top Job Matches</h3>
                                        </div>
                                        
                                        <!-- Job Cards Container -->
                                        <div style="margin-top: 16px;">
                                            {jobs_html}
                                        </div>
                                        
                                        <!-- Empty State -->
                                        <div style="display: {jobs_empty_display}; text-align: center; padding: 32px; background: #f8f9fa; border-radius: 12px; border: 2px dashed #dee2e6;">
                                            <p style="margin: 0; color: #6c757d; font-size: 15px;">No job matches today. Check back tomorrow for new opportunities!</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Hackathons Section -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td>
                                        <div style="display: flex; align-items: center; margin-bottom: 20px;">
                                            <div style="background: linear-gradient(135deg, #9B59B6, #8E44AD); width: 48px; height: 48px; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; margin-right: 14px; box-shadow: 0 4px 12px rgba(155, 89, 182, 0.3);">
                                                <span style="font-size: 24px;">🏆</span>
                                            </div>
                                            <h3 style="margin: 0; color: #1a1a1a; font-size: 22px; font-weight: 800; letter-spacing: -0.3px;">Featured Hackathons</h3>
                                        </div>
                                        
                                        <!-- Hackathon Cards Container -->
                                        <div style="margin-top: 16px;">
                                            {hackathons_html}
                                        </div>
                                        
                                        <!-- Empty State -->
                                        <div style="display: {hackathons_empty_display}; text-align: center; padding: 32px; background: #f8f9fa; border-radius: 12px; border: 2px dashed #dee2e6;">
                                            <p style="margin: 0; color: #6c757d; font-size: 15px;">No hackathons available right now. Stay tuned for exciting challenges!</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- News Section -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td>
                                        <div style="display: flex; align-items: center; margin-bottom: 20px;">
                                            <div style="background: linear-gradient(135deg, #E74C3C, #C0392B); width: 48px; height: 48px; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; margin-right: 14px; box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);">
                                                <span style="font-size: 24px;">📰</span>
                                            </div>
                                            <h3 style="margin: 0; color: #1a1a1a; font-size: 22px; font-weight: 800; letter-spacing: -0.3px;">Industry Insights</h3>
                                        </div>
                                        
                                        <!-- News Cards Container -->
                                        <div style="margin-top: 16px;">
                                            {news_html}
                                        </div>
                                        
                                        <!-- Empty State -->
                                        <div style="display: {news_empty_display}; text-align: center; padding: 32px; background: #f8f9fa; border-radius: 12px; border: 2px dashed #dee2e6;">
                                            <p style="margin: 0; color: #6c757d; font-size: 15px;">No news updates at the moment. We'll keep you informed!</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Main CTA -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 32px 0; border-top: 2px solid #f0f0f0; text-align: center;">
                                        <div style="background: linear-gradient(135deg, #FFF5F0 0%, #FFE8E0 100%); border-radius: 16px; padding: 32px; margin-bottom: 20px;">
                                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 18px; font-weight: 700; line-height: 1.5;">Ready to accelerate your career?</p>
                                            <a href="https://erflog.vercel.app/dashboard" style="display: inline-block; background: linear-gradient(135deg, #D95D39 0%, #F18F01 100%); color: white; text-decoration: none; padding: 18px 48px; border-radius: 50px; font-weight: 800; font-size: 16px; letter-spacing: 0.5px; box-shadow: 0 6px 20px rgba(217, 93, 57, 0.4); transition: transform 0.2s;">
                                                🚀 Explore Full Dashboard
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Stats Banner -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td>
                                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 24px; text-align: center; margin-bottom: 24px;">
                                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                                <tr>
                                                    <td style="text-align: center; padding: 8px;">
                                                        <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Jobs Today</p>
                                                        <p style="margin: 4px 0 0 0; color: white; font-size: 24px; font-weight: 900;">{jobs_count}</p>
                                                    </td>
                                                    <td style="text-align: center; padding: 8px;">
                                                        <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Hackathons</p>
                                                        <p style="margin: 4px 0 0 0; color: white; font-size: 24px; font-weight: 900;">{hackathons_count}</p>
                                                    </td>
                                                    <td style="text-align: center; padding: 8px;">
                                                        <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">News</p>
                                                        <p style="margin: 4px 0 0 0; color: white; font-size: 24px; font-weight: 900;">{news_count}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 0 0 20px 20px; padding: 40px 32px; text-align: center;" class="mobile-padding">
                            
                            <!-- Team Info -->
                            <div style="margin-bottom: 24px;">
                                <div style="display: inline-block; background: white; border-radius: 16px; padding: 20px 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
                                    <p style="margin: 0 0 8px 0; color: #1a1a1a; font-size: 18px; font-weight: 800;">Team Erflog</p>
                                    <p style="margin: 0; color: #666666; font-size: 14px; font-weight: 500;">Empowering Careers with AI</p>
                                </div>
                            </div>
                            
                            <!-- Contact -->
                            <div style="margin-bottom: 24px;">
                                <p style="margin: 0 0 8px 0; color: #555555; font-size: 14px; font-weight: 600;">Have questions or feedback?</p>
                                <a href="mailto:erflog.ai@gmail.com" style="color: #D95D39; text-decoration: none; font-size: 15px; font-weight: 700;">erflog.ai@gmail.com</a>
                            </div>
                            
                            <!-- Visit Website Button -->
                            <div style="margin-bottom: 24px;">
                                <a href="https://erflog.vercel.app" style="display: inline-block; background: linear-gradient(135deg, #D95D39, #F18F01); color: white; text-decoration: none; padding: 14px 36px; border-radius: 50px; font-weight: 700; font-size: 14px; letter-spacing: 0.5px; box-shadow: 0 4px 16px rgba(217, 93, 57, 0.3);">
                                    🌐 Visit Erflog Website
                                </a>
                            </div>
                            
                            <!-- Divider -->
                            <div style="height: 1px; background: linear-gradient(90deg, transparent, #d1d5db, transparent); margin: 24px 0;"></div>
                            
                            <!-- Footer Text -->
                            <p style="margin: 0 0 8px 0; color: #888888; font-size: 13px; line-height: 1.6;">
                                Sent with ❤️ by <strong style="color: #D95D39;">Erflog</strong> AI Career Platform
                            </p>
                            <p style="margin: 0 0 12px 0; color: #aaaaaa; font-size: 12px; line-height: 1.6;">
                                You're receiving this because you signed up for daily career digests.
                            </p>
                            
                            <!-- Social Links -->
                            <div style="margin-top: 20px;">
                                <p style="margin: 0 0 12px 0; color: #999999; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Connect With Us</p>
                                <div style="display: inline-flex; gap: 12px;">
                                    <a href="https://erflog.vercel.app" style="display: inline-block; width: 36px; height: 36px; background: #D95D39; border-radius: 50%; line-height: 36px; text-align: center; text-decoration: none; color: white; font-size: 16px;">🌐</a>
                                </div>
                            </div>
                            
                            <!-- Copyright -->
                            <p style="margin: 24px 0 0 0; color: #bbbbbb; font-size: 11px;">
                                © 2025 Erflog. All rights reserved.
                            </p>
                            
                        </td>
                    </tr>
                    
                    <!-- Decorative Bottom Bar -->
                    <tr>
                        <td style="background: linear-gradient(90deg, #D95D39, #F18F01, #D95D39); height: 6px; border-radius: 0 0 20px 20px;"></td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>
    """
    
    return html


class NotificationService:
    """
    Daily Email Notification Service.
    
    Sends personalized digest emails using:
    - today_data table for user's matched content
    - Gemini LLM to curate top 2 from each category
    - SMTP for email delivery
    """
    
    def __init__(self):
        """Initialize notification service."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.gemini_client = None
        
        if GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("✅ Gemini client initialized for notifications")
            except Exception as e:
                logger.error(f"❌ Gemini connection failed: {e}")
    
    def _curate_content_with_llm(
        self, 
        user_name: str,
        user_skills: list,
        target_roles: list,
        jobs: list, 
        hackathons: list, 
        news: list
    ) -> dict[str, list]:
        """
        Use LLM to intelligently pick top 2 from each category for this specific user.
        """
        if not self.gemini_client or (not jobs and not hackathons and not news):
            # Fallback: just take top 2 by score
            return {
                "jobs": sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)[:2],
                "hackathons": sorted(hackathons, key=lambda x: x.get("score", 0), reverse=True)[:2],
                "news": news[:2]
            }
        
        try:
            # Build prompt for LLM curation
            jobs_list = "\n".join([
                f"{i+1}. {j.get('title')} at {j.get('company')} (Score: {j.get('score', 0):.2f})"
                for i, j in enumerate(jobs[:6])
            ]) or "No jobs available"
            
            hackathons_list = "\n".join([
                f"{i+1}. {h.get('title')} by {h.get('company')} (Score: {h.get('score', 0):.2f})"
                for i, h in enumerate(hackathons[:6])
            ]) or "No hackathons available"
            
            news_list = "\n".join([
                f"{i+1}. {n.get('title')}"
                for i, n in enumerate(news[:5])
            ]) or "No news available"
            
            prompt = f"""You are an AI career advisor helping {user_name} with their job search.

USER PROFILE:
- Skills: {', '.join(user_skills[:8]) if user_skills else 'Various tech skills'}
- Target Roles: {', '.join(target_roles[:3]) if target_roles else 'Software Developer'}

Pick the BEST 2 items from each category that are most relevant to this user.
Consider skill match, career trajectory, and growth potential.

JOBS:
{jobs_list}

HACKATHONS:
{hackathons_list}

NEWS:
{news_list}

Return ONLY a JSON object with indices (1-based) of your picks:
{{"jobs": [1, 3], "hackathons": [2, 1], "news": [1, 2]}}

Return ONLY the JSON, no explanation."""

            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            picks = json.loads(text)
            
            # Map indices to actual items
            selected_jobs = [jobs[i-1] for i in picks.get("jobs", [1, 2])[:2] if i <= len(jobs)]
            selected_hackathons = [hackathons[i-1] for i in picks.get("hackathons", [1, 2])[:2] if i <= len(hackathons)]
            selected_news = [news[i-1] for i in picks.get("news", [1, 2])[:2] if i <= len(news)]
            
            return {
                "jobs": selected_jobs or jobs[:2],
                "hackathons": selected_hackathons or hackathons[:2],
                "news": selected_news or news[:2]
            }
            
        except Exception as e:
            logger.warning(f"LLM curation failed: {e}")
            # Fallback
            return {
                "jobs": jobs[:2],
                "hackathons": hackathons[:2],
                "news": news[:2]
            }
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send email via SMTP.
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Erflog <{SMTP_USER}>"
            msg["To"] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Connect and send
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def send_user_digest(self, user_id: str) -> dict[str, Any]:
        """
        Send daily digest email to a single user.
        """
        # Get user profile
        profile_response = self.supabase.table("profiles").select(
            "name, email, skills, target_roles"
        ).eq("user_id", user_id).execute()
        
        if not profile_response.data:
            return {"status": "error", "message": "User profile not found"}
        
        profile = profile_response.data[0]
        user_name = profile.get("name", "User")
        user_email = profile.get("email")
        user_skills = profile.get("skills", []) or []
        target_roles = profile.get("target_roles", []) or []
        
        if not user_email:
            return {"status": "skipped", "message": "No email address"}
        
        # Get today_data
        today_response = self.supabase.table("today_data").select(
            "data_json"
        ).eq("user_id", user_id).execute()
        
        if not today_response.data:
            return {"status": "skipped", "message": "No today_data available"}
        
        data = today_response.data[0].get("data_json", {})
        jobs = data.get("jobs", [])
        hackathons = data.get("hackathons", [])
        news = data.get("news", [])
        
        if not jobs and not hackathons and not news:
            return {"status": "skipped", "message": "No content to send"}
        
        # Use LLM to curate top content
        curated = self._curate_content_with_llm(
            user_name, user_skills, target_roles,
            jobs, hackathons, news
        )
        
        # Generate HTML email
        html = generate_email_html(
            user_name,
            curated["jobs"],
            curated["hackathons"],
            curated["news"]
        )
        
        # Send email
        today = datetime.now().strftime("%B %d, %Y")
        subject = f"🚀 Your Daily Career Digest - {today}"
        
        success = self._send_email(user_email, subject, html)
        
        return {
            "status": "sent" if success else "failed",
            "email": user_email,
            "jobs_count": len(curated["jobs"]),
            "hackathons_count": len(curated["hackathons"]),
            "news_count": len(curated["news"])
        }
    
    def run_daily_notifications(self) -> dict[str, Any]:
        """
        Main cron entry point: Send digest emails to all users.
        Deduplicates by email address - only sends 1 email per unique email.
        """
        logger.info("=" * 60)
        logger.info("[Notifications] Starting Daily Email Digest")
        logger.info(f"[Notifications] Timestamp: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)
        
        result = {
            "status": "success",
            "emails_sent": 0,
            "emails_failed": 0,
            "emails_skipped": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Fetch all users with email
            users_response = self.supabase.table("profiles").select(
                "user_id, email"
            ).not_.is_("email", "null").execute()
            
            if not users_response.data:
                logger.warning("No users with email found")
                result["status"] = "no_users"
                return result
            
            # Deduplicate by email - use first user_id for each email
            email_to_user = {}
            for user in users_response.data:
                email = user.get("email")
                user_id = user.get("user_id")
                if email and user_id and email not in email_to_user:
                    email_to_user[email] = user_id
            
            logger.info(f"Found {len(email_to_user)} unique emails to notify")
            
            for email, user_id in email_to_user.items():
                try:
                    email_result = self.send_user_digest(user_id)
                    
                    if email_result["status"] == "sent":
                        result["emails_sent"] += 1
                    elif email_result["status"] == "skipped":
                        result["emails_skipped"] += 1
                    else:
                        result["emails_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process user {user_id}: {e}")
                    result["emails_failed"] += 1
            
            if result["emails_failed"] > 0:
                result["status"] = "partial_success"
                
        except Exception as e:
            logger.error(f"Critical error in daily notifications: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        logger.info("=" * 60)
        logger.info(f"[Notifications] Complete: Sent={result['emails_sent']}, Failed={result['emails_failed']}, Skipped={result['emails_skipped']}")
        logger.info("=" * 60)
        
        return result


# Singleton instance
_notification_service: Optional[NotificationService] = None

def get_notification_service() -> NotificationService:
    """Get or create singleton notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
