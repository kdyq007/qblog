# -*- coding:utf-8 -*-

from extensions import celery
from lib.mail import send_mail

@celery.task(name="mail.send_reg_mail", queue="qblog_async")
def send_reg_mail(receiver):
    subject = "qiv5注册邮件"
    content = '''
    恭喜您注册qiv5.com成功，请点击以下链接激活您的账户：
    <a href="http://qiv5.com">http://qiv5.com</a>

    '''
    send_mail(receiver=receiver, subject=subject, content=content)

# send_reg_mail(["kdyq@vip.qq.com"])