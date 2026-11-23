# BookMyShow

A movie-ticket booking application with an Angular client and a set of FastAPI
services. The backend supports movie/show discovery, seat holds, payment intents,
and event-driven notification handling.

## Architecture

| Component | Port | Responsibility |
| --- | ---: | --- |
| Angular client | 4200 | Movie discovery, seat selection, and checkout |
| API gateway | 8000 | HTTP/WebSocket proxy, JWT validation, and CORS |
| User service | 8004 | Account registration, login, and profile lookup |
| Cinema service | 8005 | Cinema management |
| Hall service | 8006 | Hall and seat-layout management |
| Movie service | 8007 | Movie metadata management |
| Catalog service | 8001 | Cities, cinemas, halls, movies, and showtimes |
| Booking service | 8002 | Seat maps, temporary seat holds, and booking state |
| Payment service | 8003 | Payment intents and webhook processing using a mock gateway |
| Notification worker | — | Consumes booking/payment events from RabbitMQ |

The gateway routes client requests to the services. User, catalog, booking,
payment, cinema, hall, and movie data use the shared MongoDB database configured
by `MONGO_DB_NAME` (default: `BookMyShow`). The catalog serves cities and
showtimes; booking and payment store bookings and transactions. Redis backs
catalog caching and seat holds. RabbitMQ carries booking/payment events to the
notification worker.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- MongoDB (a MongoDB Atlas cluster or a local instance)
- Redis and RabbitMQ reachable from the host

## Local setup

1. Create a virtual environment and install the backend dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e libs/common \
     -r gateway/requirements.txt \
     -r services/catalog/requirements.txt \
     -r services/booking/requirements.txt \
     -r services/payment/requirements.txt \
     -r services/movies/requirements.txt \
     -r services/notification/requirements.txt \
     -r services/user/requirements.txt
   ```

2. Configure the root environment file:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `MONGO_URI` to your MongoDB connection string. Keep
   `MONGO_DB_NAME=BookMyShow`. The example file uses placeholder MongoDB
   credentials and must be configured before running the backend. Start Redis
   and RabbitMQ locally and make sure they are reachable on the configured
   ports. Set `REDIS_HOST` and `RABBITMQ_HOST` to `localhost`;
   `CATALOG_SERVICE_URL` and `USER_SERVICE_URL` should point to their local
   ports (`8001` and `8004`).

   Set `CORS_ORIGINS` to a JSON array containing the browser origins allowed to
   call the gateway. The defaults allow Angular development on
   `http://localhost:4200` and `http://127.0.0.1:4200`. Change the development
   `JWT_SECRET` before using this application outside local development.

3. Seed sample catalog data. This upserts the sample cities, cinemas, hall,
   movie, and a future show; it is safe to run more than once.

   ```bash
   .venv/bin/python scripts/seed_db.py
   ```

4. Start the backend services and notification worker:

   ```bash
   ./scripts/dev.sh
   ```

   The script starts the user, gateway, catalog, booking, payment, cinema, hall,
   and movie APIs with reload enabled, plus the notification worker. Press
   **Ctrl-C** to stop them.

5. In another terminal, install and start the Angular client:

   ```bash
   cd client
   npm ci
   npm start
   ```

   Open `http://localhost:4200`.

The HTTP APIs expose interactive documentation at
`http://localhost:8000/docs` (gateway), `http://localhost:8001/docs` (catalog),
`http://localhost:8002/docs` (booking), `http://localhost:8003/docs` (payment),
`http://localhost:8004/docs` (user), and `http://localhost:8007/docs` (movies).
Register and log in through
`POST /api/v1/auth/register` and `POST /api/v1/auth/login`; use the returned
Bearer token for protected routes such as `GET /api/v1/users/me` and
`GET /api/v1/bookings?user_id=<user-id>`. The gateway accepts the booking
collection URL with or without a trailing slash and forwards the authenticated
user identity to the booking service. The notification worker is a background
consumer and does not expose an HTTP API.

## License

This project is licensed under the Apache License 2.0. See [LICENSE.md](./LICENSE.md).
Replace the copyright-holder placeholder in that file with the appropriate
copyright owner before distributing the project.
