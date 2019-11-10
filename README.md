# Mapping Asia (web)

## How to run
```
ssh mappingasia-rds-dev -Nv
redis-server
FLASK_APP=api.py FLASK_DEBUG=1 python3 -m flask run
cd react-dashboard > npm start
```

## Conda environment
env file: `conda-env.yml`

## DEMO (https://jisunglim.github.io/mappingasia-web/)