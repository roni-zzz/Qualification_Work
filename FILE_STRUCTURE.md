# Alarm System - File Structure Documentation

## Root Level Files
- **docker-compose.yml** - Docker Compose configuration for running backend, frontend, and database services in containers
- **LICENSE** - Project license file
- **README.md** - Main project documentation and overview
- **VERSION.txt** - Current version of the project
- **FILE_STRUCTURE.md** - This file; documentation of all project files

---

## Backend (`backend/`)

### Root Backend Files
- **run.py** - Entry point to start the FastAPI backend server
- **requirements.txt** - Production Python dependencies
- **requirements-dev.txt** - Development Python dependencies (testing, linting tools)
- **pytest.ini** - Pytest configuration for running tests
- **Dockerfile** - Docker image configuration for the backend service

### `backend/app/` - Main Application Code
- **main.py** - FastAPI application setup, route registration, middleware configuration
- **__init__.py** - Package initialization
- **alarm.py** - Core alarm system logic and operations
- **config.py** - Application configuration (environment variables, settings)
- **dependencies.py** - Dependency injection setup (database, services, authentication)
- **security.py** - JWT authentication, password hashing, security utilities
- **rate_limit.py** - Rate limiting middleware to prevent abuse
- **validate2.py** - Input validation and data sanitization functions

### `backend/app/models/` - Data Models
- **request_models.py** - Pydantic models for API request validation
- **response_models.py** - Pydantic models for API response formatting

### `backend/app/routers/` - API Route Handlers
- **admin.py** - Admin management endpoints (users, permissions, system configuration)
- **alarm.py** - Alarm control endpoints (arm, disarm, status)
- **auth.py** - Authentication endpoints (login, registration, token refresh)
- **events.py** - Event logging and retrieval endpoints
- **warehouse.py** - Smart warehouse management endpoints (rooms, devices, automation)
- **notifications.py** - Notification settings and push notification endpoints
- **pairing.py** - Device pairing and microcontroller registration endpoints
- **users.py** - User profile and settings management endpoints

### `backend/app/services/` - Business Logic
- **auth_service.py** - Authentication service (user login, token generation, verification)
- **event_service.py** - Event logging and management service
- **notification_service.py** - Notification delivery (Firebase Cloud Messaging integration)
- **otp_service.py** - One-time password generation and verification for 2FA

### `backend/db/` - Database Layer
- **connectToDB.py** - PostgreSQL database connection and pool management
- **ensure_schema.py** - Database schema initialization and versioning
- **workflow.sql** - SQL schema definition (tables, relationships, constraints)
- **migrations/** - Database migration scripts for schema updates

#### Database Query Modules
- **insertIntoDB.py** - Insert operations for users, devices, events, alarms
- **admin_queries.py** - Admin-specific database queries (user management, system stats)
- **Roles.py** - User role and permission management queries
- **warehouse_roles.py** - Smart warehouse room and device role assignments
- **sensor_labels.py** - Sensor naming and labeling queries
- **fcm_tokens.py** - Firebase Cloud Messaging token storage and retrieval
- **device_last_seen.py** - Device activity tracking
- **events.py** - Event logging and retrieval queries
- **pending_disarm.py** - Pending disarm request management

#### Device Management
- **addAvailableSystems.py** - Register available alarm systems
- **connectToAlarmSystem.py** - Establish connection to alarm systems
- **connectMCtoAlarmSystem.py** - Connect microcontroller to alarm system
- **getMicrocontrollerBySystem.py** - Retrieve microcontroller info for a system
- **setModeAlarmSystem.py** - Change alarm system mode (armed/disarmed)
- **getModeOfSystem.py** - Get current alarm system mode

#### Authentication & Setup
- **googleAuth.py** - Google OAuth integration for authentication
- **firebase-service-account.json** - Firebase service account credentials

#### Configuration & Documentation
- **postgresql.conf** - PostgreSQL server configuration
- **README_SETUP.md** - Database setup and initialization instructions
- **db.txt** - Database connection notes or environment info
- **setup_db.sh** - Bash script for database initialization
- **setup_db.ps1** - PowerShell script for database initialization

### `backend/scripts/` - Utility Scripts
- **run_migration_and_set_admin.py** - Run database migrations and create admin user
- **ensure_password_admin.py** - Ensure admin account password is set
- **setup_two_test_accounts.py** - Create test user accounts for development
- **send_test_events.py** - Generate test events for development/testing

### `backend/tests/` - Integration Tests
- **conftest.py** - Pytest fixtures and configuration
- **test_api.py** - API endpoint integration tests
- **test_validate.py** - Input validation tests

### `backend/unit_tests/` - Unit Tests
- **test_config.py** - Configuration loading tests
- **test_db_methods.py** - Database query function tests
- **test_event_service.py** - Event service logic tests
- **test_rate_limit.py** - Rate limiting tests
- **test_rate_limit_load.py** - Rate limiting load/performance tests
- **test_request_models.py** - Request model validation tests
- **test_security.py** - Security and authentication tests
- **test_send_test_events.py** - Test event generation tests
- **test_validate2.py** - Input validation function tests

---

## Frontend (`frontend/`)

### Build Configuration
- **build.gradle.kts** - Root-level Gradle build configuration
- **settings.gradle.kts** - Gradle project structure definition
- **gradle.properties** - Gradle build properties and flags
- **gradlew** / **gradlew.bat** - Gradle wrapper scripts (Unix/Windows)
- **local.properties** - Local development machine configuration (SDK paths)
- **Dockerfile** - Docker image configuration for the Android app build
- **gradle/libs.versions.toml** - Centralized dependency version management

### `frontend/app/` - Android App Module
- **build.gradle.kts** - Android app-specific build configuration and dependencies
- **proguard-rules.pro** - ProGuard/R8 code obfuscation rules for release builds
- **google-services.json** - Google Firebase configuration
- **src/** - Source code (Android Activities, Fragments, UI, tests)
- **build/** - Compiled build artifacts and outputs

---

## Microcontroller (`microcontroller/`)

### Main Code Files
- **main.py** - Entry point; initializes system, WiFi connection, main event loop
- **boot.py** - MicroPython boot sequence and early initialization
- **_main.py** - Alternative/backup main file or development version

### Functional Modules
- **api.py** - HTTP API client to communicate with backend
- **_api.py** - Alternative/backup API implementation
- **config.py** - Microcontroller configuration (WiFi, server URLs, sensors)
- **_config.py** - Alternative/backup configuration
- **events.py** - Event detection and handling (sensor triggers, alarms)
- **_events.py** - Alternative/backup events implementation
- **wifi.py** - WiFi connection management and network utilities
- **_wifi.py** - Alternative/backup WiFi implementation
- **ina219.py** - INA219 power monitoring sensor driver

### Sensor & Hardware
- **scan_networks.py** - WiFi network scanning utility

### Configuration & Documentation
- **requirements.txt** - MicroPython package dependencies
- **req.json** - Alternative requirements format
- **Dockerfile** - Docker image for microcontroller development/testing
- **notes.md** - Development notes and implementation details
- **src/** - Source code directory (production versions of main modules)

---

## Images (`Images/`)
- Reserved for project diagrams, screenshots, or architecture images

---

## Summary by Purpose

**Backend**: FastAPI REST API for alarm system management, user authentication, event logging, smart warehouse control, and database operations.

**Frontend**: Android mobile app for controlling the alarm system, viewing events, managing devices, and receiving notifications.

**Microcontroller**: MicroPython firmware for embedded devices that interface with physical sensors and alarm hardware, communicating with the backend via HTTP API.
