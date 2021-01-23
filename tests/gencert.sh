#!/bin/bash
# Run this to generate a new self-signed cert for localhost for the purposes of
# integration testing

# One-liner for subjectAltName from:
# http://www.scispike.com/blog/openssl-subjectaltname-one-liner/
HERE=$(dirname "$(readlink -f "$0")")
openssl req -newkey rsa:2048 -nodes -keyout "$HERE"/key.pem -x509 -days 10000 -out "$HERE"/cert.pem -subj '/CN=127.0.0.1' \
    -extensions SAN \
    -config <( cat /etc/ssl/openssl.cnf \
    <(printf "[SAN]
subjectAltName='IP.1:127.0.0.1,DNS.1:localhost'

[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name

[req_distinguished_name]"))
