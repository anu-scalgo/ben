#!/bin/bash
# Launch Adminer locally using PHP built-in server

if ! command -v php &> /dev/null; then
    echo "PHP is required but not installed."
    exit 1
fi

echo "Starting Adminer at http://0.0.0.0:8080"
echo "Login with System: PostgreSQL, Server: 127.0.0.1, User: postgres, Pass: postgres, DB: dumacle"
php -S 0.0.0.0:8080 -t scripts/adminer/
