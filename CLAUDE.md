## Development Tips
- Use uv run instead of manually activating the virtualenv
- Use `just dev` to start PostgreSQL and Django (most common workflow)
- Use `just dev-all` to start all services including JupyterLab and Vite
- Logs are written to `logs/dev.log` for debugging

## Accessing Development Logs
When you need to debug issues or see what's happening:
- Read the log file directly: `cat logs/dev.log` or `tail -n 100 logs/dev.log`
- Use the provided commands:
  - `just logs` - View last 50 lines
  - `just logs -n 100` - View last 100 lines
  - `just logs-follow` - Watch logs in real-time
  - `just logs-grep ERROR` - Filter for specific patterns
- The log file contains output from all services with ANSI colors stripped
- Browser console messages can be accessed via Playwright MCP's `browser_console_messages()` function

## Project Overview
This is a Django-based personal website/blog implementing IndieWeb standards with Wagtail CMS integration.

## Development Environment
- Python 3.12+ with uv for dependency management
- PostgreSQL database (use local Docker container for development)
- Redis for background tasks (production only)
- Use `uv run` prefix for all Python commands

## Key Commands
- `just dev` - Start PostgreSQL and Django development server
- `just dev-all` - Start all services (includes JupyterLab and Vite)
- `just test` - Run test suite
- `just coverage` - Run tests with coverage report
- `just db-migrate` - Create and apply database migrations
- `just shell` - Enhanced Django shell
- `just logs-follow` - Watch development logs in real-time
- `just cleanup` - Kill any leftover development processes

## Code Style
- Black formatter with 119 character line length
- isort with Black profile for import sorting
- Follow existing patterns in the codebase
- Use type hints where appropriate

## Testing
- Use pytest for all tests (not Django's unittest)
- Test files go in `homepage/tests/` or app-specific `tests/` directories
- Run tests before committing changes
- Aim for high test coverage on new code

## Django Apps Structure
- Core functionality: `homepage.core` (includes webmention integration)
- User management: `homepage.users`
- Federation support: `homepage.fedi`
- Micropub implementation: `homepage.micropub`

## Third-Party Integration
- django-cast: Blog/podcast functionality
- django-indieweb: IndieWeb protocol support
- Wagtail: CMS features
- django-allauth: Authentication

## Frontend Development
- Bootstrap 5 theme via cast-bootstrap5
- Vue.js components via cast-vue
- Static files in `homepage/static/`
- Templates in `homepage/templates/`

## Database
- Always create migrations for model changes
- Use factory-boy for test data generation
- Be careful with data migrations in production

## Deployment
- Staging: `uv run python commands.py deploy_staging`
- Production: `uv run python commands.py deploy_production`
- Use environment variables for sensitive configuration
- Static files served via WhiteNoise

## Important Conventions
- Environment-specific settings in `config/settings/`
- Use django-environ for environment variables
- Follow Django best practices and conventions
- Keep security in mind (never commit secrets)

## Git Workflow
- Create feature branches for new work
- Write clear, descriptive commit messages
- Test thoroughly before pushing
- Use conventional commits format when appropriate
