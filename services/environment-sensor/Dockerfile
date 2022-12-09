# nosemgrep:github.workflows.config.dockerfile-source-not-pinned
FROM python:3-slim
LABEL maintainer="Charlie Lewis <clewis@iqt.org>"
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y build-essential libjpeg62-turbo-dev zlib1g-dev
RUN python3 -m pip install -U pip
WORKDIR /
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY *.py /
ARG VERSION
ENV VERSION $VERSION
# nosemgrep:github.workflows.config.missing-user
ENTRYPOINT ["python3", "/environment_app.py"]
# nosemgrep:github.workflows.config.missing-user
CMD [""]
