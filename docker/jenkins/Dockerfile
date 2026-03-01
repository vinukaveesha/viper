FROM jenkins/jenkins:2.552

# Preinstall required plugins so the UI includes Credentials + Pipeline.
COPY docker/jenkins/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Seed admin user and optional credentials on first boot.
COPY docker/jenkins/init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
