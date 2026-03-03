#!/bin/sh
# Fix JENKINS_HOME ownership for rootless Podman (volume may be created with different UID).
chown -R jenkins:jenkins /var/jenkins_home 2>/dev/null || true

if [ "$(id -u)" = "0" ]; then
  exec runuser -u jenkins -- /usr/bin/tini -s -- /usr/local/bin/jenkins.sh "$@"
else
  exec /usr/bin/tini -s -- /usr/local/bin/jenkins.sh "$@"
fi
