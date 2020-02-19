FROM python:3.7

RUN pip install --no-cache python-telegram-bot==12.0.0 requests==2.18.4 retrying==1.3.3 google-cloud-firestore==1.6.0

COPY bot.py /src/
COPY keyfile.json /src/
WORKDIR /src/

CMD ["python", "bot.py"]
