# Copilot Instructions for Traffic Counter Desktop Application

This is a traffic counting application with dual architecture:
- **Frontend**: Flet-based Python desktop application (`frontend/`) for data collection and counting
- **Backend**: Django REST API (`auth/`) for authentication, data management, and work assignment

## Environment Setup

**Platform:** Windows 11
**Working Directories:**
- **Frontend Desktop App**: `c:\Users\lucas.melo\traffic-count\frontend\`
- **Django Backend**: `c:\Users\lucas.melo\traffic-count\auth\`

**Python Dependencies:**
- Frontend: Flet 0.21.1, pynput, SQLAlchemy, aiohttp
- Backend: Django 5.1.3, djangorestframework, PostgreSQL

**Development Commands:**
```powershell
# Frontend Desktop App (main entry point)
.\venv\Scripts\Activate.ps1 ; cd frontend ; python main.py

# Django Backend Server (REQUIRED for frontend to work)
.\venv\Scripts\Activate.ps1 ; cd auth ; python manage.py runserver

# CSS Build (TailwindCSS)
npm run build:css
```

**IMPORTANT Terminal Usage Guidelines:**
- **DO NOT create multiple terminals in VS Code** - use one terminal at a time to avoid confusion
- **Always check if a terminal is already running** before creating a new one
- **ALWAYS activate venv first** - every Python command must start with `.\venv\Scripts\Activate.ps1`
- **Both services must be running**: Django backend (port 8000) + Flet frontend
- **Frontend main.py location**: `traffic-count/frontend/main.py` (NOT in project root)
- **Working directory for frontend**: Always `cd frontend` before running `python main.py`

## Architecture Overview

**Dual System Design:**
- **Frontend (`frontend/`)**: Flet desktop app for traffic counting with local SQLite database
- **Backend (`auth/`)**: Django REST API for user management, work assignments, and data centralization

**Frontend Components:**
- **Main App (`app/contador.py`)**: Core application with service manager pattern
- **UI Tabs (`app/ui/`)**: Início, Contagem, Histórico, Config, Relatório, Edição Períodos  
- **Services (`app/services/`)**: SessionManager, ApiManager, ExcelManager, HistoryManager, UIManager
- **Database (`database/models.py`)**: SQLite with Sessao, Categoria, Historico tables
- **Authentication Flow (`main.py`)**: JWT token management with Django backend

**Backend Django Apps:**
- **autenticacao**: Custom User model with setor-based permissions (CON, DIG, P&D, SUPER, ENG, ADM)
- **contagens**: Session and counting data management
- **trabalhos**: Project hierarchy (Cliente → Codigo → Ponto) with role-based CRUD
- **padroes**: Vehicle counting patterns and user preferences
- **tickets**: Ticket/task management system
- **updates**: Version control and updates

**Data Flow:**
1. User authenticates through Django API → JWT tokens stored locally
2. Session created in desktop app → Synced to Django backend
3. Counting happens locally → Periodic sync to Django
4. Reports generated from local SQLite → Excel exports to network drive

**Runtime Dependencies:**
- **Django Backend MUST be running** on port 8000 for frontend to function
- **PostgreSQL database** must be accessible for Django
- **Local SQLite database** created automatically for frontend
- **Network connectivity** required between frontend and backend APIs

## Critical Patterns

**Service Manager Pattern:**
All business logic encapsulated in service classes injected into main `ContadorPerplan`:
```python
# In contador.py
self.session_manager = SessionManager(self)
self.api_manager = ApiManager(self)
self.excel_manager = ExcelManager(self)
self.history_manager = HistoryManager(self)
self.ui_manager = UIManager(self)
```

**Session State Management:**
- `contador.sessao` = current session ID (string)
- `contador.details` = session metadata dict with Código, Ponto, Data, etc.
- `contador.contagens` = in-memory counting data `{(vehicle, movement): count}`
- `contador.current_timeslot` = current 15-minute period for auto-saves

**Authentication & Authorization:**
- JWT tokens from Django stored in `AUTH_TOKENS_FILE` (user's home/Contador/auth_tokens.json)
- Role-based access: `can_edit()` function checks for 'supervis' in user.setor
- API requests auto-include `Authorization: Bearer <token>` headers

**Django Permission System:**
```python
# trabalhos/views.py - Role checking
def can_edit(user):
    # Allows superusers, staff, and users with 'supervis' in cargo/setor
    if user.is_superuser or user.is_staff:
        return True
    # Check profile.cargo or user.cargo for 'supervis'
    if hasattr(user, 'cargo') and 'supervis' in cargo.lower():
        return True
```

**Flet Version Compatibility:**
- Uses Flet 0.21.1 - ALWAYS use `ft.Colors.` and `ft.Icons.` (capital C/I)
- UI components stored in `contador.ui_components` dict for cross-tab access
- Threading with `session_lock` for database operations

## Database Schema

**Frontend SQLite (`contadordb.db`):**
```python
Sessao: sessao(PK), padrao, codigo, ponto, data, horario_inicio, status, movimentos(JSON)
Categoria: id(PK), padrao, veiculo, movimento, bind, count  
Historico: id(PK), sessao(FK), categoria_id(FK), movimento, timestamp, acao
```

**Backend PostgreSQL:**
```python
# autenticacao.User - Custom user with setor field
User: username, email, setor(CON/DIG/P&D/SUPER/ENG/ADM), preferences(JSON)

# contagens - Session tracking
Session: sessao, codigo, ponto, data, usuario, status, movimentos(JSON)
Counting: session(FK), veiculo, movimento, count, timestamp

# trabalhos - Project hierarchy  
Cliente: nome
Codigo: cliente(FK), codigo, descricao
Ponto: codigo(FK), nome, localizacao
PontoDetail: ponto(FK), movimento, observacao, created_at
PontoDetailImage: detail(FK), image

# padroes - Vehicle counting patterns
PadraoContagem: pattern_type, veiculo, bind
UserPadraoContagem: user(FK), pattern_type, veiculo, bind
```

## Development Workflows

**Virtual Environment Management:**
- **ALWAYS activate venv before running Python scripts:** `venv\Scripts\activate`
- **Working directory:** `frontend/` (contains main.py, app/, database/, etc.)
- **Python executable when venv active:** `python` (resolves to venv Python)
- **Frontend main entry point:** `traffic-count/frontend/main.py` (NOT in project root)

**Terminal Best Practices:**
- **Use only ONE terminal at a time** - avoid creating multiple terminals in VS Code
- **Check active terminals** before creating new ones to prevent confusion
- **Always navigate to correct directory** before running commands

**Adding New UI Components:**
1. Create in `app/ui/aba_[name].py` extending `ft.Column`
2. Add to `contador.ui_components` in setup_ui()
3. Reference via `self.contador.ui_components['name']` in services
4. **Important**: UI components must implement `force_ui_update()` method for session resuming

**UI Update Patterns:**
- Use `setup_ui()` for initial UI construction
- Use `force_ui_update()` for refreshing UI with new session data (categories, binds)
- Never call `setup_ui()` during normal operations - only `force_ui_update()`

**Testing & Debugging:**
```powershell
# Frontend App (from project root)
.\venv\Scripts\Activate.ps1 ; cd frontend ; python main.py

# Django Backend
.\venv\Scripts\Activate.ps1 ; cd auth ; python manage.py runserver

# Database migrations
.\venv\Scripts\Activate.ps1 ; cd auth ; python manage.py makemigrations
.\venv\Scripts\Activate.ps1 ; cd auth ; python manage.py migrate

# Create superuser
.\venv\Scripts\Activate.ps1 ; cd auth ; python manage.py createsuperuser
```

**API Integration:**
- All API calls through `utils/api.py` `async_api_request()`
- Headers auto-include JWT: `{"Authorization": f"Bearer {tokens['access']}"}`
- Django endpoints: `/auth/`, `/contagens/`, `/padroes/`, `/trabalhos/`

**Error Handling:**
- Use logging with module name: `logging.error(f"[ERROR] {message}")`
- Show user feedback via `ft.SnackBar` in page.overlay
- Database errors must rollback: `session.rollback()`

## Key Files to Reference

- `app/contador.py` - Main application class with all managers
- `app/services/session_manager.py` - Session lifecycle management  
- `database/models.py` - SQLAlchemy schema
- `utils/config.py` - Environment configuration
- `main.py` - App entry point with authentication flow
- `auth/trabalhos/views.py` - Django project hierarchy management
- `auth/autenticacao/models.py` - Custom User model with setor permissions
- `auth/padroes/models.py` - Vehicle counting patterns

**Never modify** `main.py` authentication flow or `utils/config.py` without understanding Django API dependencies.

## Integration Points

**Django API Sync:**
- Sessions must be created both locally and remotely
- Counts synced every save via `api_manager.send_count_to_django()`
- Use numeric session IDs from Django for final operations

**Excel Export:**
- Files saved to network drive (`EXCEL_BASE_DIR`) or local fallback
- Template-based with openpyxl, data from local DB

**Keyboard Binds:**
- pynput listener maps keys to vehicle/movement combinations
- Binds loaded from Django per pattern type, cached locally
- Configurable via `utils/change_binds.py` UI dialog

**Project Hierarchy:**
- Cliente → Codigo → Ponto structure managed in `auth/trabalhos/`
- Role-based permissions: only users with 'supervis' in setor can edit
- Frontend loads available códigos/pontos for session creation

## Critical Reminders for AI Agents

**Terminal Management in VS Code:**
- **NEVER create multiple terminals** - VS Code should only have one active terminal at a time
- **Always check existing terminals** before running commands to avoid confusion and conflicts
- **Use terminal consolidation** - reuse the same terminal for all operations in a session
- **Avoid terminal proliferation** - multiple terminals lead to lost context and execution errors

**Code Explanation Policy:**
- **ALWAYS explain code changes in beginner-friendly terms**
- Break down what each modification does step-by-step
- Explain WHY the change is needed, not just WHAT is being changed
- Use analogies and simple language for complex concepts
- Show before/after comparisons when helpful

**Windows 11 Specific:**
- Use PowerShell commands for terminal operations
- File paths use backslashes: `frontend\app\contador.py`
- Always activate virtual environment: `venv\Scripts\activate`

**Required Before Any Python Execution:**
```powershell
# ALWAYS run this first (from project root)
cd c:\Users\lucas.melo\traffic-count
.\venv\Scripts\Activate.ps1

# Then navigate to frontend for app operations
cd frontend
python main.py
```

**Critical Path Information:**
- **Frontend main.py location**: `traffic-count/frontend/main.py` (NOT in project root)
- **Always use single terminal**: Do not create multiple terminals in VS Code
- **Always activate venv first**: Every Python command must start with `.\venv\Scripts\Activate.ps1`
- **Working directory sequence**: project root → activate venv → cd frontend → run main.py

**Common Issues:**
- Windows PowerShell uses `;` as command separator, NOT `&&`
- Flet version 0.21.1 requires `ft.Colors.` and `ft.Icons.` (capital letters)
- Virtual environment is at project root, not in frontend folder
- UI components must have `force_ui_update()` method for session resuming
- Database operations require `session_lock` for thread safety

## UI/UX Design Guidelines

**Color Contrast and Accessibility:**
- **NEVER use light background with light text** - creates unreadable content
- **ALWAYS prioritize dark themes** for better readability and user experience
- **Apply color theory principles** to ensure proper contrast ratios
- **Test readability** before implementing any color scheme

**Flet Color Best Practices:**
```python
# ❌ BAD: Light background + Light text (unreadable)
ft.Container(
    bgcolor=ft.Colors.GREY_50,     # Light background
    content=ft.Text("Text", color=ft.Colors.GREY_300)  # Light text
)

# ✅ GOOD: Dark theme with proper contrast
ft.Container(
    bgcolor=ft.Colors.GREY_900,    # Dark background
    content=ft.Text("Text", color=ft.Colors.WHITE)  # Light text
)

# ✅ GOOD: Light theme with proper contrast  
ft.Container(
    bgcolor=ft.Colors.WHITE,       # Light background
    content=ft.Text("Text", color=ft.Colors.BLACK)  # Dark text
)
```

**Recommended Color Palettes:**
- **Primary Dark Theme**: `bgcolor=ft.Colors.GREY_900`, `color=ft.Colors.WHITE`
- **Success Messages**: `bgcolor=ft.Colors.GREEN_700`, `color=ft.Colors.WHITE`
- **Warning Messages**: `bgcolor=ft.Colors.ORANGE_700`, `color=ft.Colors.WHITE`
- **Error Messages**: `bgcolor=ft.Colors.RED_700`, `color=ft.Colors.WHITE`
- **Info Messages**: `bgcolor=ft.Colors.BLUE_700`, `color=ft.Colors.WHITE`

**Status Indicators:**
```python
# Status container with proper contrast
status_container = ft.Container(
    bgcolor=ft.Colors.GREY_800,  # Dark background
    content=ft.Text("Status", color=ft.Colors.WHITE),  # Light text
    border_radius=8,
    padding=10
)
```

**Accessibility Requirements:**
- **Minimum contrast ratio**: 4.5:1 for normal text
- **Enhanced contrast ratio**: 7:1 for better accessibility
- **Test with color blindness** simulators when possible
- **Provide alternative indicators** beyond color (icons, text)

**Color Psychology Application:**
- **Green**: Success, confirmation, go-ahead actions
- **Red**: Errors, warnings, stop actions  
- **Orange/Yellow**: Caution, pending states, attention needed
- **Blue**: Information, neutral actions, primary buttons
- **Grey**: Disabled states, secondary information
