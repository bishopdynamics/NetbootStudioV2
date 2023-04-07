FROM lscr.io/linuxserver/code-server:latest


ARG CODE_RELEASE
ARG SERVICE_USER
ARG SERVICE_GROUP
ARG SERVICE_UID
ARG SERVICE_GID
LABEL build_version="BishopDynamics version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="BishopDynamics"

# add local files
COPY /root /

RUN groupadd -g ${SERVICE_GID} ${SERVICE_GROUP}
RUN useradd ${SERVICE_USER} -u ${SERVICE_UID} -g ${SERVICE_GID} -m -s /bin/bash

# ports and volumes
EXPOSE 8443
