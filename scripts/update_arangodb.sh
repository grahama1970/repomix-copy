# docker exec arangodb  arangodump --output-directory /data/backup --overwrite true

# docker exec arangodb mkdir -p /data/backup

docker exec arangodb arangodump --output-directory /data/backup --overwrite true --server.password 'openSesame'
