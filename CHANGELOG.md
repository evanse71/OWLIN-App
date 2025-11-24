# Changelog

All notable changes to the OWLIN upload system will be documented in this file.

## [v0.1.0-rc1] – 2025-10-02

### Added
- Health banner & backend reachability guard
- Centralized API base URL (VITE_API_BASE_URL)
- Upload endpoint with disk persistence + optional OCR
- Smoke tests (happy path + edge cases)
- CI route assertions & E2E gate
- Support pack script
- Structured logging with timestamps
- Automatic uploads directory creation at startup
- Edge case handling (404, CORS, permissions, empty files)
- OCR graceful degradation when dependencies missing

### Fixed
- "0% stuck" uploads now show exact error text
- Generic error messages replaced with specific, actionable feedback
- Configuration drift prevented with single environment variable
- Startup reliability with automatic directory creation

### Changed
- Single source of truth for API URL (VITE_API_BASE_URL only)
- Removed NEXT_PUBLIC_API_BASE_URL references
- Enhanced error handling with "Copy error" functionality
- Improved logging format for better debugging

### Security
- CORS configuration for all development ports
- File upload validation and sanitization
- Graceful error handling prevents information leakage

### Notes
- Single source of truth for API URL. Remove NEXT_PUBLIC_API_BASE_URL.
- OCR is now optional - uploads work even if OCR dependencies are missing
- All tests passing: E2E, edge cases, route assertions
- Production-ready with comprehensive hardening
