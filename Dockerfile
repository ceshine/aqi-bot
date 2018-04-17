FROM python:3.6.4-alpine3.7

RUN pip install --no-cache python-telegram-bot==10.0.0 requests==2.18.4 retrying==1.3.3

COPY bot.py /src/
WORKDIR /src/

CMD ["python", "bot.py"]
