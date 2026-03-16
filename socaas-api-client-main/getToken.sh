#!/bin/bash

curl -s -X POST "https://customerapiauth.fortinet.com/api/v1/oauth/token/" \
     -H "Content-Type: application/json" \
     -d '{"username": "62A1AFE0-0119-46FB-8AC8-9D2D04315BEE", "password": "4466cf63a03ffa0d99aa921967a6c5db!1Aa", "client_id": "socaas", "grant_type": "password"}'