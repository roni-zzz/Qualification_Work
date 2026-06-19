# Warehouse Alarm System

A comprehensive IoT-based alarm management system for warehouse environments featuring real-time monitoring, push notifications, device pairing, and multi-user management.

## Features

- Real-time alarm arm/disarm control
- Firebase push notifications
- IoT device pairing and management
- Multi-user access with role-based control
- Two-factor authentication
- Event logging and history
- Rate limiting and security middleware
- Docker support for easy deployment

## Architecture

- **Backend:** FastAPI (Python) with PostgreSQL
- **Frontend:** Android Kotlin application
- **Microcontroller:** ESP32 with MicroPython
- **Database:** PostgreSQL 12+

## API Endpoints

- `POST /api/auth/login` - User login
- `GET /api/alarm/status` - Get alarm status
- `POST /api/alarm/arm` - Arm system
- `POST /api/alarm/disarm` - Disarm system
- `GET /api/events/list` - View events
- `POST /api/pairing/register` - Register device
- `POST /api/notifications/register` - Register FCM token

Full documentation at `/docs` endpoint.

## License

See LICENSE file.

## Repository

https://github.com/roni-zzz/Qualification_Work

---

For detailed documentation, see:
- [Backend README](backend/README.md)
- [Database Setup](backend/db/README_SETUP.md)
- [File Structure](FILE_STRUCTURE.md)
