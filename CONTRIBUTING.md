# Contributing

## Setup

1. Install Python 3.11+ and Node 20+.
2. Run `make doctor` to validate local toolchain versions.
3. Run `make setup`.
4. Start local services with `make dev`.

For local non-Docker runs, copy env templates first:

- `cp backend/.env.example backend/.env`
- `cp frontend/.env.example frontend/.env`

## Quality checks

Run:

- `make lint`
- `make test`

## Demo data bootstrap

After backend startup, load synthetic patients and run baseline scoring:

- `make demo-bootstrap`
