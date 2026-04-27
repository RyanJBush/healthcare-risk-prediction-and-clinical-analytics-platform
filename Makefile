.RECIPEPREFIX := >

.PHONY: doctor setup dev lint test backend-test frontend-build demo-bootstrap

doctor:
>python -c "import sys; assert sys.version_info >= (3, 11), f'Python 3.11+ required, found {sys.version.split()[0]}'; print('Python check: OK')"
>node -e "const [major]=process.versions.node.split('.').map(Number); if (major < 20) { console.error('Node 20+ required, found ' + process.versions.node); process.exit(1); } console.log('Node check: OK')"
>docker --version >/dev/null && echo "Docker check: OK"

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

demo-bootstrap:
>./scripts/bootstrap_demo.sh
