docker build -t 3269964641/data-display-service:latest ./data-display
docker build -t 3269964641/data-processing-service:latest ./data-processing
docker build -t 3269964641/city-search-service:latest ./city-search

docker push 3269964641/data-display-service
docker push 3269964641/data-processing-service
docker push 3269964641/city-search-service