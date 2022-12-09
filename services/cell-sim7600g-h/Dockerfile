# nosemgrep:github.workflows.config.dockerfile-source-not-pinned
FROM debian:stable-slim
RUN apt-get update && apt-get install -y iproute2 udhcpc libqmi-utils
COPY start-modem.sh /start-modem.sh
# nosemgrep:github.workflows.config.missing-user
ENTRYPOINT ["/start-modem.sh"]
ARG VERSION
ENV VERSION $VERSION
# nosemgrep:github.workflows.config.missing-user
CMD [""]
