#!/bin/sh
# 10 requests per 10 seconds per IP on /api/query. Run with CF_AUTH_TOKEN set.
curl -sX PUT \
  "https://api.cloudflare.com/client/v4/zones/1d7c35fee8d563c3b2ae7c4e55b61bc7/rulesets/phases/http_ratelimit/entrypoint" \
  -H "Authorization: Bearer $CF_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [
      {
        "ratelimit": {
          "characteristics": ["ip.src", "cf.colo.id"],
          "period": 10,
          "requests_per_period": 10,
          "requests_to_origin": false,
          "mitigation_timeout": 10
        },
        "description": "User DB read limits",
        "expression": "(http.request.uri.path eq \"/api/query\")",
        "action": "block",
        "enabled": true
      }
    ]
  }' | python3 -c "import sys,json;d=json.load(sys.stdin);r=(d.get('result') or {}).get('rules',[{}])[0].get('ratelimit',{});print('ok' if d.get('success') else d.get('errors'), '->', r.get('requests_per_period'), 'per', r.get('period'), 's')"
