#!/bin/sh
# Only substitute ${BACKEND_URL}; leave all nginx runtime variables ($host,
# $proxy_host, $remote_addr, $scheme, etc.) untouched.
envsubst '${BACKEND_URL}' \
  < /etc/nginx/templates/ink.conf.template \
  > /etc/nginx/conf.d/ink.conf

exec nginx -g 'daemon off;'
