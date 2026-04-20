.RECIPEPREFIX := >

.PHONY: setup dev lint test backend-test frontend-build

setup:
>python -m pip install -r ./backend/requirements.txt
>python -m pip install -e "./backend[dev]"
>npm --prefix ./frontend install

dev:
>docker compose -f ./docker-compose.yml up --build

lint:
>cd ./backend && ruff check app tests
>cd ./frontend && npm run lint

test: backend-test frontend-build

backend-test:
>cd ./backend && DATABASE_URL=sqlite+pysqlite:///./nova_test.db pytest -q

frontend-build:
>cd ./frontend && npm run build
