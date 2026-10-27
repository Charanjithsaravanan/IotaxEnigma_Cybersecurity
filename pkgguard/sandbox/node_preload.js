'use strict';

const fs = require('fs');
const dns = require('dns');
const http = require('http');
const https = require('https');

const logPath = process.env.SANDBOX_RUNTIME_LOG || '/logs/runtime.jsonl';
function log(event, fields = {}) {
  try {
    fs.appendFileSync(logPath, JSON.stringify({ event, ...fields }) + '\n');
  } catch (_) {
    // Tracing must never change package behavior if the log volume is unavailable.
  }
}

const originalEnv = process.env;
process.env = new Proxy(originalEnv, {
  get(target, property, receiver) {
    if (typeof property === 'string') log('env_read', { key: property });
    return Reflect.get(target, property, receiver);
  },
});

const originalLookup = dns.lookup;
dns.lookup = function (hostname, ...args) {
  log('dns_lookup', { host: String(hostname) });
  return originalLookup.call(this, hostname, ...args);
};

function wrapRequest(original, scheme) {
  return function (options, ...args) {
    let host = '';
    let port;
    let path = '/';
    if (typeof options === 'string') {
      try {
        const url = new URL(options);
        host = url.hostname;
        port = url.port ? Number(url.port) : undefined;
        path = url.pathname + url.search;
      } catch (_) {
        host = options;
      }
    } else if (options && typeof options === 'object') {
      host = options.hostname || options.host || '';
      port = options.port;
      path = options.path || path;
    }
    log('http_request', {
      scheme,
      host: String(host),
      port: port || (scheme === 'https' ? 443 : 80),
      url: `${scheme}://${host}${path}`,
    });
    return original.call(this, options, ...args);
  };
}
http.request = wrapRequest(http.request, 'http');
https.request = wrapRequest(https.request, 'https');
