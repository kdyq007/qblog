# -*- coding:utf-8 -*-


from flask import current_app

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.mime.image import MIMEImage
import smtplib
import time
from email import Utils


def send_mail(receiver, subject, content, ctype="html", pics=()):
    if not receiver:
        return
    """subject and body are unicode objects"""
    sender = current_app.config.get("DEFAULT_MAIL_SENDER")
    smtpserver = current_app.config.get("MAIL_SERVER")
    smtpport = current_app.config.get("MAIL_PORT")
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    if ctype == "html":
        msg = MIMEText(content, 'html', 'utf-8')
    else:
        msg = MIMEText(content, 'plain', 'utf-8')

    if len(pics) != 0:
        msgRoot = MIMEMultipart('related')
        msgText = MIMEText(content, 'html', 'utf-8')
        msgRoot.attach(msgText)
        i = 1
        for pic in pics:
            fp = open(pic, "rb")
            image = MIMEImage(fp.read())
            fp.close()
            image.add_header('Content-ID', '<img%02d>' % i)
            msgRoot.attach(image)
            i += 1
        msg = msgRoot

    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender
    if isinstance(receiver, (list, tuple)):
        msg['To'] = ';'.join(receiver)
    else:
        msg['To'] = receiver
    msg['Message-ID'] = Utils.make_msgid()
    msg['date'] = time.strftime('%a, %d %b %Y %H:%M:%S %z')
    retry = 0
    while retry < 10:
        try:
            if current_app.config.get("DEBUG"):
                smtp = smtplib.SMTP_SSL(smtpserver, smtpport)
                smtp.login(username, password)
                smtp.sendmail(sender, receiver, msg.as_string())
                smtp.quit()
            current_app.logger.info("send email to %s success"%receiver)
            break
        except Exception as e:
            current_app.logger.error(
                "send email to %s unknown error, %s" % (receiver, str(e)))
            retry += 1
            time.sleep(5)


