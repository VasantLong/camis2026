import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def send_email(to: str, subject: str, body_html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
        s.sendmail(settings.smtp_from, [to], msg.as_string())


def send_welcome_email(to: str, display_name: str) -> None:
    send_email(
        to=to,
        subject="欢迎注册 CAMIS",
        body_html=f"""<html><body>
<h2>欢迎加入 CAMIS，{display_name}！</h2>
<p>您的账号已注册成功。</p>
<p>请登录系统申请角色，管理员审核通过后即可使用完整功能。</p>
<hr>
<p style="color:#888;font-size:12px">此邮件由 CAMIS 系统自动发送（开发环境 Mailpit 捕获），请勿回复。</p>
</body></html>""",
    )
