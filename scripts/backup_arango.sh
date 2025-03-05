# docker exec arangodb arangodump \
#   --output-directory /var/lib/arangodb3/backup \
#   --server.database verifaix \
#   --server.username root \
#   --server.password 'openSesame' \
#   --overwrite true \
#   --threads 2 \
#   --batch-size 500 \
#   --compress-output true \
#   --progress true 
 


docker cp arangodb:/var/lib/arangodb3/backup ~/arangodb_backup

# verify the backup
ls -l ~/arangodb_backup