# nosemgrep:github.workflows.config.dockerfile-source-not-pinned
FROM alpine:3.17
RUN apk update && apk add alsa-utils alsa-utils-doc alsa-lib alsaconf alsa-ucm-conf bash ffmpeg
RUN addgroup root audio
COPY asound.conf /etc/asound.conf
COPY record.sh /record.sh
ARG VERSION
ENV VERSION $VERSION
# nosemgrep:github.workflows.config.missing-user
ENTRYPOINT ["/record.sh"]
# nosemgrep:github.workflows.config.missing-user
CMD [""]
