from uuid import uuid4
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, render_template_string
from models import Invite
from extentions import db
from tasks.email_tasks import send_onboarding_email_task

def create_and_queue_invite(email, name, onboarding_base_url, purpose, created_by_id, ttl_days=7, send_async=True):
    """
    Create an Invite DB row, generate token, build bodies, and queue the Celery task.
    Returns invite_id on success, None on failure.
    """
    # Validate email and url before calling this helper
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps({"email": email, "nonce": uuid4().hex})

    safe_url = f"{onboarding_base_url.rstrip('/')}/accept-invite?token={token}"

    subject = current_app.config.get("ONBOARDING_SUBJECT", "Welcome to ThesisVault")
    text_body = f"Hello {name},\n\nYou've been invited to join ThesisVault for: {purpose}.\n\nPlease complete your registration by clicking the link below:\n\n{safe_url}\n\nIf you did not expect this invitation, please ignore this email."
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        @media only screen and (max-width: 620px) {
          table.body .content { padding: 0 !important; }
          table.body .container { padding: 0 !important; width: 100% !important; }
          table.body .main { border-radius: 0 !important; }
        }
      </style>
    </head>
    <body style="background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; margin: 0; padding: 0;">
      <table border="0" cellpadding="0" cellspacing="0" class="body" style="border-collapse: separate; width: 100%; background-color: #f8fafc;">
        <tr>
          <td style="display: block; margin: 0 auto; max-width: 580px; padding: 10px; width: 580px;">
            <div class="content" style="box-sizing: border-box; display: block; margin: 0 auto; max-width: 580px; padding: 10px;">
              
              <!-- START CENTERED WHITE CONTAINER -->
              <table role="presentation" class="main" style="border-collapse: separate; width: 100%; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; border-spacing: 0;">
                
                <!-- START MAIN CONTENT AREA -->
                <tr>
                  <td class="wrapper" style="box-sizing: border-box; padding: 40px;">
                    <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%;">
                      <tr>
                        <td>
                          <!-- LOGO / HEADER -->
                          <div style="margin-bottom: 30px;">
                            <span style="font-size: 24px; font-weight: 900; color: #4f46e5; letter-spacing: -0.025em;">ThesisVault</span>
                          </div>
                          
                          <p style="font-size: 16px; font-weight: normal; margin: 0; margin-bottom: 20px; color: #1e293b;">Hello {{ name }},</p>
                          
                          <p style="font-size: 16px; font-weight: normal; margin: 0; margin-bottom: 24px; line-height: 1.6; color: #475569;">
                            You've been invited to join <strong>ThesisVault</strong> for: <span style="color: #6366f1; font-weight: 600;">{{ purpose }}</span>. 
                            Our platform helps you manage research submissions and streamline the grading workflow with AI-powered insights.
                          </p>
                          
                          <table border="0" cellpadding="0" cellspacing="0" class="btn btn-primary" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; box-sizing: border-box; margin-bottom: 30px;">
                            <tbody>
                              <tr>
                                <td align="left" style="font-size: 16px; vertical-align: top; padding-bottom: 15px;">
                                  <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: auto;">
                                    <tbody>
                                      <tr>
                                        <td style="border-radius: 8px; text-align: center; background-color: #4f46e5;"> <a href="{{ url }}" target="_blank" style="border: solid 1px #4f46e5; border-radius: 8px; box-sizing: border-box; color: #ffffff; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 30px; text-decoration: none; text-transform: capitalize;">Complete Registration</a> </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </td>
                              </tr>
                            </tbody>
                          </table>
                          
                          <p style="font-size: 14px; font-weight: normal; margin: 0; margin-bottom: 15px; color: #94a3b8; line-height: 1.5;">
                            If the button doesn't work, copy and paste this link into your browser:
                            <br>
                            <span style="word-break: break-all; color: #6366f1;">{{ url }}</span>
                          </p>
                          
                          <hr style="border: 0; border-bottom: 1px solid #f1f5f9; margin: 30px 0;">
                          
                          <p style="font-size: 12px; font-weight: normal; margin: 0; color: #64748b;">
                            This invitation was sent by your organization administrator. If you did not expect this invitation, please ignore this email.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <!-- START FOOTER -->
              <div class="footer" style="clear: both; margin-top: 20px; text-align: center; width: 100%;">
                <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%;">
                  <tr>
                    <td class="content-block" style="color: #94a3b8; font-size: 12px; text-align: center; padding-top: 10px; padding-bottom: 10px;">
                      <span>&copy; 2026 ThesisVault SaaS Platform</span>
                    </td>
                  </tr>
                </table>
              </div>
            </div>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    html_body = render_template_string(html_template, name=name, purpose=purpose.replace('_', ' ').capitalize(), url=safe_url)

    invite = Invite(
        email=email,
        name=name,
        token=token,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        purpose=purpose,
        created_by_id=created_by_id,
        expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        status="queued"
    )
    db.session.add(invite)
    db.session.commit()

    # Queue the worker with the invite id only
    if send_async and current_app.config.get("USE_CELERY"):
        send_onboarding_email_task.delay(invite.id)
    else:
        # Optionally call the task synchronously for small installs
        send_onboarding_email_task(invite.id)

    return invite.id

