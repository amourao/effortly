FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements_full.txt /code/
RUN  pip install -r requirements_full.txt --no-dependencies
RUN python manage.py collectstatic
COPY . /code/

