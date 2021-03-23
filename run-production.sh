#!/bin/bash

mkdir -p /app/media/uploads /app/media/student_pics /app/static/  /app/static/CACHE/
chown -R sis:sis /app/media/uploads /app/media/student_pics /app/static/

exec "$@"
