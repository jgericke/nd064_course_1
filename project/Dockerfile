FROM python:2.7

COPY techtrends /techtrends
WORKDIR /techtrends
RUN set -x \
    && pip install -r requirements.txt \
    && python init_db.py
EXPOSE 3111
CMD [ "python", "app.py" ]