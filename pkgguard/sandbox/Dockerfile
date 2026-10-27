FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl python3 python3-pip python3-setuptools nodejs npm strace \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /logs /input /app/site-packages /root/.ssh /root/.aws \
    && printf '%s\n' '----- honeypot canary -----' > /root/.ssh/id_rsa \
    && printf '%s\n' '[default]' 'aws_access_key_id=canary' 'aws_secret_access_key=canary' > /root/.aws/credentials \
    && printf '%s\n' 'SANDBOX_CANARY=do-not-use' > /app/.env \
    && chmod 600 /root/.ssh/id_rsa /root/.aws/credentials

ENV AWS_SECRET_ACCESS_KEY=canary-aws-secret \
    GITHUB_TOKEN=canary-github-token \
    OPENAI_API_KEY=canary-openai-key \
    STRIPE_SECRET_KEY=canary-stripe-key \
    PYTHONPATH=/opt/sandbox-hooks:/app/site-packages \
    NODE_OPTIONS=--require=/opt/sandbox-hooks/node_preload.js \
    SANDBOX_RUNTIME_LOG=/logs/runtime.jsonl

COPY sitecustomize.py node_preload.js trace_runner.sh parse_trace.py /opt/sandbox-hooks/
RUN chmod 755 /opt/sandbox-hooks/trace_runner.sh
ENTRYPOINT ["/opt/sandbox-hooks/trace_runner.sh"]
