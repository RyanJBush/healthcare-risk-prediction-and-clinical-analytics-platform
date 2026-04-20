.RECIPEPREFIX := >

.PHONY: setup dev lint test backend-test frontend-build

setup:
>python -m pip install -r /home/runner/work/nova-ai/nova-ai/backend/requirements.txt
>python -m pip install -e "/home/runner/work/nova-ai/nova-ai/backend[dev]"
>npm --prefix /home/runner/work/nova-ai/nova-ai/frontend install

dev:
>docker compose -f /home/runner/work/nova-ai/nova-ai/docker-compose.yml up --build

lint:
>cd /home/runner/work/nova-ai/nova-ai/backend && ruff check app tests
>cd /home/runner/work/nova-ai/nova-ai/frontend && npm run lint

test: backend-test frontend-build

backend-test:
>cd /home/runner/work/nova-ai/nova-ai/backend && DATABASE_URL=sqlite+pysqlite:///./nova_test.db pytest -q

frontend-build:
>cd /home/runner/work/nova-ai/nova-ai/frontend && npm run build
