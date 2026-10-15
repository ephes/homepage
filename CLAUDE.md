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
- PostgreSQL database (local installation required for development)
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
- Staging: `just deploy-staging`
- Production: `just deploy-production`
- Use environment variables for sensitive configuration
- Static files served via WhiteNoise

## Important Conventions
- Environment-specific settings in `config/settings/`
- Use django-environ for environment variables
- Follow Django best practices and conventions
- Keep security in mind (never commit secrets)

## Katharina's Portfolio, CV and Cover Letter: Where Content, Images and Code Live
Scope: this applies **only** to Katharina's design portfolio (`homepage.portfolio`) and to her
CV and cover letter built with the django-resume `editorial` theme. It does not apply to the
blog, podcast, IndieWeb, fediverse, other resume themes or any other part of this repository
or of django-resume.

Portfolio:

| Where | What |
|---|---|
| Database (Wagtail) | All portfolio texts; every text must be editable in Wagtail |
| Object store (Wagtail images) | All portfolio images; every image must be replaceable in Wagtail |
| This repository | All portfolio code and fixed design elements: the animated handwriting (e.g. "Let's talk about", "that's me", "together"), "Moin", fonts, linen texture, line icons |

- Field defaults in models stay neutral or empty: no personal data or editorial copy (e-mail,
  social links, profile text). Plain interface labels ("Zur Startseite") may keep a default.
- Moving content between databases (e.g. staging → production) must not require retyping it;
  it is transferred from the database, not kept as text in code.

CV and cover letter (`editorial` theme):

| Where | What |
|---|---|
| Database | All personal text: cover-letter text, address, positions, skills and every other CV content |
| Object store | Katharina's portrait photo |
| django-resume repository | Theme code and its public design elements: rotated section headings, handwritten headlines, drawn background illustrations |

- Both repositories are public on purpose; anyone may use the theme's background illustrations.

## Git Workflow
- Create feature branches for new work
- Write clear, descriptive commit messages
- Test thoroughly before pushing
- Use conventional commits format when appropriate

## Local Development with Editable Dependencies
When working on dependencies like django-cast or cast-vue:

1. **Switch to local editable mode:**
   ```bash
   uv run commands.py switch-to-dev-environment
   ```
   This modifies `pyproject.toml` to use local paths in `[tool.uv.sources]`

2. **Switch back to git sources:**
   ```bash
   uv run commands.py switch-to-git-sources
   ```

3. **prek hook:** A prek hook automatically prevents committing local paths. If you try to commit while in dev mode, it will:
   - Detect local paths in `tool.uv.sources`
   - Automatically switch back to git sources
   - Require you to stage the corrected `pyproject.toml`

**Note:** The prek hook ensures you never accidentally commit local development paths.
