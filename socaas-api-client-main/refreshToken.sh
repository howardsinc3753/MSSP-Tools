#!/bin/bash

# Variables
API_URL="https://customerapiauth.fortinet.com/api/v1/oauth/token/"
CLIENT_ID="socaas"
REFRESH_TOKEN=""
GRANT_TYPE="refresh_token"

# cURL Command
curl -H "Content-Type: application/json" \
     -X POST "$API_URL" \
     -d '{
           "client_id": "'"$CLIENT_ID"'",
           "refresh_token":"'"$REFRESH_TOKEN"'",
           "grant_type": "'"$GRANT_TYPE"'"
         }'