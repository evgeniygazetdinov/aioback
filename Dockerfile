FROM python:3.12-alpine
COPY . /photo_gesture_checker/

RUN ls

WORKDIR /photo_gesture_checker
RUN ls

RUN apk update && apk add \
    python3-dev \
    musl-dev \
    gcc \
    && pip install -r requirements.txt \
    && pip install virtualenv \
RUN python3 -m virtualenv --python=python3 virtualenv
EXPOSE 8888
RUN ls
CMD python3 manage.py