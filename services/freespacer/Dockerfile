# nosemgrep:github.workflows.config.dockerfile-source-not-pinned
FROM python:3.11-alpine
LABEL maintainer="Charlie Lewis <clewis@iqt.org>"
ENV PYTHONUNBUFFERED 1
RUN apk update && apk add coreutils
COPY freespacer_app.py /freespacer_app.py
ARG VERSION
ENV VERSION $VERSION
# nosemgrep:github.workflows.config.missing-user
ENTRYPOINT ["python3", "/freespacer_app.py"]
# nosemgrep:github.workflows.config.missing-user
CMD [""]
