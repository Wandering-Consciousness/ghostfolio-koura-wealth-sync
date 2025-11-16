#!/bin/bash

if [ -n "$CRON" ]; then
    echo "Setting up cron job with schedule: $CRON"
    echo "$CRON cd /usr/app/src && python main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/koura-sync
    chmod 0644 /etc/cron.d/koura-sync
    crontab /etc/cron.d/koura-sync
    touch /var/log/cron.log
    cron && tail -f /var/log/cron.log
else
    echo "Running sync once"
    python main.py
fi
