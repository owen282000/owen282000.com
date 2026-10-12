# A static site: Caddy serves the files in site/ and nothing else.
FROM caddy:2-alpine
# Caddy ships with the capability to bind low ports. It listens on 8080 here, and the
# container runs with no-new-privileges, which refuses to start a binary that carries one.
RUN apk add --no-cache libcap && setcap -r /usr/bin/caddy && apk del libcap
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY site /srv
USER 65532:65532
EXPOSE 8080
