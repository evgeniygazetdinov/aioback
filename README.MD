

### для локального запуска

python3 -m venv venv
pip install -r requirements.txt

### docker
docker-compose -f local-compose.yml build
docker-compose -f local-compose.yml up -d