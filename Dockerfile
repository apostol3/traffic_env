FROM python:3.6-alpine
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add git

RUN pip install git+http://github.com/apostol3/pynlab
ADD main.py /
ADD traffic_env.py /