"""AI News Automation Bot package."""
"""News bot package initialization."""

import os

# Avast injects a device-style SSLKEYLOGFILE path on this Windows machine;
# OpenSSL cannot use that path and terminates HTTPS clients before requests
# are made. The Windows trust store below retains certificate verification.
os.environ.pop("SSLKEYLOGFILE", None)

import truststore

# On Windows, use the OS certificate store. This supports locally trusted
# corporate/antivirus HTTPS inspection certificates without weakening TLS.
truststore.inject_into_ssl()
