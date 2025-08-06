# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a traffic counting application with a dual architecture:
- **Frontend**: Flet-based Python desktop application for data collection and counting
- **Backend**: Django REST API for authentication, data management, and work assignment

## Common Development Commands

### Virtual Environment & Setup
```powershell
# ALWAYS activate virtual environment first (from project root)
.\venv\Scripts\Activate.ps1

# Frontend Desktop App (main entry point)
cd frontend
python main.py

# Django Backend Server (REQUIRED for frontend to work)
cd auth
python manage.py runserver

# CSS Build (TailwindCSS)
npm run build:css
```

### Database Management
```powershell
# Django migrations (from auth/ directory)
python manage.py makemigrations
python manage.py migrate

# Create Django superuser
python manage.py createsuperuser
```

### Development Workflow
1. **Always activate venv first**: `.\venv\Scripts\Activate.ps1`
2. **Run Django backend**: `cd auth && python manage.py runserver` (port 8000)
3. **Run frontend in separate terminal**: `cd frontend && python main.py`
4. **Both services must be running** for full functionality

## Architecture Overview

### High-Level Structure
- **`frontend/`**: Flet desktop application with SQLite database
- **`auth/`**: Django backend with PostgreSQL database
- **`package.json`**: TailwindCSS build configuration for Django templates

### Frontend Architecture (`frontend/`)
- **`main.py`**: Application entry point with authentication flow
- **`app/contador.py`**: Main application class using service manager pattern
- **`app/services/`**: Business logic services (SessionManager, ApiManager, ExcelManager, etc.)
- **`app/ui/`**: UI components organized by tabs (Início, Contagem, Histórico, Config, etc.)
- **`database/models.py`**: SQLite schema with SQLAlchemy
- **`utils/`**: Configuration, API utilities, and helper functions

### Backend Architecture (`auth/`)
- **`backend/settings.py`**: Django configuration with PostgreSQL
- **`autenticacao/`**: Custom User model with role-based permissions (setor field)
- **`contagens/`**: Session and counting data management
- **`trabalhos/`**: Project hierarchy (Cliente → Codigo → Ponto)
- **`padroes/`**: Vehicle counting patterns and user preferences
- **`tickets/`**: Task management system
- **`updates/`**: Version control

### Key Patterns

#### Service Manager Pattern
All business logic is encapsulated in service classes:
```python
# In contador.py
self.session_manager = SessionManager(self)
self.api_manager = ApiManager(self)
self.excel_manager = ExcelManager(self)
```

#### Authentication Flow
- JWT tokens from Django stored locally in `auth_tokens.json`
- All API requests include `Authorization: Bearer <token>` headers
- Role-based access via `setor` field in User model

#### Data Synchronization
1. Sessions created in desktop app → Synced to Django backend
2. Counting happens locally in SQLite → Periodic sync to Django
3. Reports generated from local data → Excel exports

## Database Schema

### Frontend SQLite (`contadordb.db`)
- **Sessao**: Session metadata with JSON movimentos field
- **Categoria**: Vehicle/movement combinations with key bindings
- **Historico**: Counting action history with timestamps

### Backend PostgreSQL
- **User**: Custom user model with setor-based permissions
- **Session/Counting**: Centralized session and count data
- **Cliente/Codigo/Ponto**: Project hierarchy
- **PadraoContagem**: Vehicle counting patterns

## Development Guidelines

### Terminal Management
- **Use only ONE terminal at a time** to avoid confusion
- **Always activate venv first** before running Python commands
- **Check working directory**: frontend commands from `frontend/`, Django from `auth/`

### UI Development (Flet 0.21.1)
- Use `ft.Colors.` and `ft.Icons.` (capital letters)
- Components must implement `force_ui_update()` method
- Access cross-tab components via `self.contador.ui_components`
- Use dark themes with proper contrast for readability

### API Integration
- All API calls through `utils/api.py` `async_api_request()`
- Django endpoints: `/auth/`, `/contagens/`, `/padroes/`, `/trabalhos/`
- Handle authentication failures gracefully

### Error Handling
- Use logging with module names: `logging.error(f"[ERROR] {message}")`
- Show user feedback via `ft.SnackBar`
- Database operations require `session_lock` for thread safety

## Important File Locations

### Key Frontend Files
- `frontend/main.py` - Application entry point
- `app/contador.py` - Main application class
- `database/models.py` - SQLAlchemy schema
- `utils/config.py` - Environment configuration

### Key Backend Files
- `auth/backend/settings.py` - Django configuration
- `auth/autenticacao/models.py` - Custom User model
- `auth/trabalhos/views.py` - Project hierarchy with permissions
- `auth/contagens/models.py` - Session and counting models

## Runtime Requirements

- **PostgreSQL database** accessible for Django backend
- **Both Django (port 8000) and frontend must run simultaneously**
- **Network connectivity** between frontend and backend
- **Windows 11** environment with PowerShell
- **Virtual environment** must be activated for all Python operations

---

# 🚀 BUILDING A SUPER PROJECT: Beginner to Pro Guide

*Think of this as your mentor teaching you how to build professional-grade software*

## 📋 Phase 1: Project Planning (The Foundation)

### Step 1: Define Your Project Vision
**What we're doing:** Creating a clear roadmap before writing any code
**Why it matters:** Like building a house, you need blueprints before laying bricks

```markdown
## Project Definition Template
1. **What problem does this solve?** (One sentence)
2. **Who will use this?** (Target users)
3. **What are the core features?** (3-5 main things it does)
4. **How will users interact with it?** (Web, desktop, mobile, API)
5. **What's the success criteria?** (How do you know it works?)
```

**Example from our traffic counter:**
- **Problem:** Manual traffic counting is slow and error-prone
- **Users:** Traffic engineers and data collectors
- **Core features:** Count vehicles, save data, generate reports, manage users
- **Interface:** Desktop app + web admin panel
- **Success:** Counts are accurate and 10x faster than manual

### Step 2: Choose Your Architecture
**What we're doing:** Deciding how the pieces fit together
**Think of it like:** Designing the rooms in your house

**Simple Project (MVP):**
```
Frontend (What users see) → Backend (Business logic) → Database (Data storage)
```

**Complex Project (Like ours):**
```
Desktop App (Local work) ↔ REST API (Sync data) ↔ Web Admin (Management)
     ↓                           ↓                        ↓
SQLite (Local DB)          PostgreSQL (Central DB)   Admin Interface
```

**Beginner tip:** Start simple, grow complex. MVP first!

### Step 3: Technology Stack Selection
**What we're doing:** Choosing your tools
**Like choosing:** The right tools for building a house

**Decision Framework:**
```python
# Ask these questions for each choice:
1. Do I know this technology? (Learning curve)
2. Does it solve my problem? (Functionality)
3. Is it actively maintained? (Community support)
4. Will it scale? (Future growth)
5. Can I get help? (Documentation/tutorials)
```

**Our choices explained:**
- **Frontend:** Flet (Python GUI) - Familiar language, cross-platform
- **Backend:** Django (Python web framework) - Batteries included, great admin
- **Database:** PostgreSQL - Reliable, scales well
- **API:** Django REST Framework - Integrates perfectly with Django

## 🏗️ Phase 2: Project Structure (The Skeleton)

### Step 4: Create Professional Project Structure
**What we're doing:** Organizing code so you (and others) can find things
**Like organizing:** A filing cabinet - everything has its place

```
project-name/
├── README.md                 # What this project does
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore              # Don't commit these files
├── CLAUDE.md               # AI assistant guidance
├── frontend/               # User interface code
│   ├── main.py            # Application entry point
│   ├── app/               # Core application logic
│   │   ├── __init__.py    # Makes it a Python package
│   │   ├── models/        # Data structures
│   │   ├── services/      # Business logic
│   │   └── ui/           # User interface components
│   ├── utils/            # Helper functions
│   └── tests/            # Test files
├── backend/              # Server-side code
│   ├── manage.py         # Django management script
│   ├── config/           # Settings and configuration
│   ├── apps/             # Django applications
│   │   ├── users/        # User management
│   │   ├── core/         # Core functionality
│   │   └── api/          # API endpoints
│   └── tests/            # Server tests
└── docs/                 # Documentation
    ├── setup.md          # How to install
    ├── api.md            # API documentation
    └── deployment.md     # How to deploy
```

**Why this structure works:**
- **Separation of concerns:** Frontend and backend are separate
- **Modularity:** Each folder has one responsibility
- **Scalability:** Easy to add new features
- **Team-friendly:** Others can navigate easily

### Step 5: Set Up Development Environment
**What we're doing:** Creating your workspace
**Like setting up:** A workshop with all the right tools

```powershell
# Step 5.1: Create virtual environment (isolated Python space)
python -m venv venv
# Why: Keeps project dependencies separate from system Python

# Step 5.2: Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # Mac/Linux
# Why: Now Python commands use project-specific packages

# Step 5.3: Install base dependencies
pip install django djangorestframework python-dotenv
# Why: Core tools for web development

# Step 5.4: Save dependencies (so others can recreate your environment)
pip freeze > requirements.txt
# Why: Like a recipe - others can make the same setup
```

**Pro tip:** Always create `requirements.txt` and `.env.example` files!

## 🔨 Phase 3: Development Workflow (Building the House)

### Step 6: Start with Database Design
**What we're doing:** Planning how data is stored and connected
**Think of it as:** Designing filing cabinets before putting papers in them

```python
# Example: Traffic Counter Database Design
class User(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    role = models.CharField(max_length=50)  # What they can do
    created_at = models.DateTimeField(auto_now_add=True)

class Session(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Who created it
    status = models.CharField(max_length=20)  # Active, Complete, etc.
    data = models.JSONField(default=dict)  # Flexible data storage
    created_at = models.DateTimeField(auto_now_add=True)

# Why this design works:
# 1. Each table has one responsibility
# 2. Relationships are clear (ForeignKey)
# 3. Timestamps for debugging
# 4. Flexible data field for complex info
```

**Database design principles:**
1. **One table, one concept** (Users table only stores user info)
2. **Use relationships** (ForeignKey connects tables)
3. **Plan for queries** (How will you search this data?)
4. **Add timestamps** (When was this created/updated?)

### Step 7: Build API First (Backend-First Development)
**What we're doing:** Creating the "brain" before the "face"
**Why this order:** Frontend needs data to display

```python
# Step 7.1: Create basic API endpoint
# backend/apps/api/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def session_list(request):
    """Get all sessions for current user"""
    # This is what your frontend will call
    sessions = Session.objects.filter(user=request.user)
    return Response({
        'sessions': [
            {
                'id': s.id,
                'name': s.name,
                'status': s.status,
                'created_at': s.created_at
            } for s in sessions
        ]
    })

# Step 7.2: Test the API manually
# Use Postman, curl, or Django REST framework browser
# GET http://localhost:8000/api/sessions/
# Should return JSON data
```

**API development workflow:**
1. **Design endpoint** (What URL, what data?)
2. **Write view function** (What does it do?)
3. **Test manually** (Does it work?)
4. **Write automated test** (So it keeps working)
5. **Document it** (So others know how to use it)

### Step 8: Build Frontend Components
**What we're doing:** Creating the user interface
**Like building:** The control panel of a car

```python
# Step 8.1: Create reusable components
# frontend/app/ui/session_list.py
import flet as ft

class SessionList(ft.Column):
    def __init__(self, api_manager):
        super().__init__()
        self.api_manager = api_manager
        self.sessions = []
        
    async def load_sessions(self):
        """Get sessions from API and update UI"""
        try:
            # Call our backend API
            response = await self.api_manager.get('/api/sessions/')
            self.sessions = response.get('sessions', [])
            
            # Update UI with new data
            self.build_session_list()
            self.update()
            
        except Exception as e:
            # Always handle errors gracefully
            self.show_error(f"Could not load sessions: {e}")
    
    def build_session_list(self):
        """Create UI elements from data"""
        self.controls.clear()
        
        for session in self.sessions:
            self.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        title=ft.Text(session['name']),
                        subtitle=ft.Text(f"Status: {session['status']}"),
                        trailing=ft.Text(session['created_at'][:10])  # Date only
                    )
                )
            )
```

**Component design principles:**
1. **Single responsibility** (This component only shows session list)
2. **Reusable** (Can be used anywhere in the app)
3. **Data-driven** (Gets data from API, not hardcoded)
4. **Error handling** (What if API fails?)
5. **User feedback** (Loading states, error messages)

## 🧪 Phase 4: Quality Assurance (Making Sure It Works)

### Step 9: Testing Strategy
**What we're doing:** Proving your code works correctly
**Like:** Quality control in a factory - test before shipping

```python
# Step 9.1: Unit Tests (Test individual functions)
# backend/apps/api/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Session

class SessionTestCase(TestCase):
    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_session(self):
        """Test that we can create a session"""
        session = Session.objects.create(
            name='Test Session',
            user=self.user,
            status='Active'
        )
        
        # Check it was created correctly
        self.assertEqual(session.name, 'Test Session')
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.status, 'Active')
    
    def test_api_endpoint(self):
        """Test API returns correct data"""
        # Create test session
        Session.objects.create(name='Test', user=self.user, status='Active')
        
        # Login as test user
        self.client.force_login(self.user)
        
        # Call API
        response = self.client.get('/api/sessions/')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['sessions']), 1)

# Run tests with: python manage.py test
```

**Testing levels explained:**
1. **Unit tests:** Test one function at a time
2. **Integration tests:** Test how parts work together
3. **System tests:** Test the whole application
4. **User acceptance tests:** Test from user's perspective

### Step 10: Code Quality Tools
**What we're doing:** Automatic code review
**Like having:** A proofreader check your writing

```powershell
# Step 10.1: Install quality tools
pip install black flake8 mypy pytest

# Step 10.2: Format code automatically
black .  # Makes code look consistent
# Why: Consistent formatting = easier to read

# Step 10.3: Check for problems
flake8 .  # Finds potential bugs and style issues
# Why: Catches mistakes before they become bugs

# Step 10.4: Type checking
mypy .  # Checks if you're using variables correctly
# Why: Prevents type-related bugs

# Step 10.5: Add to your workflow
# Create .pre-commit-hooks.yaml to run these automatically
```

**Quality checklist:**
- [ ] Code is formatted consistently
- [ ] No unused imports or variables
- [ ] Functions have docstrings (explain what they do)
- [ ] Error handling is present
- [ ] Tests cover main functionality

## 🚀 Phase 5: Deployment & Maintenance (Going Live)

### Step 11: Environment Configuration
**What we're doing:** Making your app work in different places
**Like:** Making sure your car works in different climates

```python
# Step 11.1: Environment variables (.env file)
# These change between development and production
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/dbname
API_URL=http://localhost:8000

# Step 11.2: Settings configuration
# backend/config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Step 11.3: Create different environment files
# .env.development  (for your computer)
# .env.production   (for live server)
# .env.example      (template for others)
```

### Step 12: Documentation
**What we're doing:** Writing instructions for humans
**Like:** Creating a user manual for your software

```markdown
# README.md template
# Project Name

Brief description of what this does.

## Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment: `cp .env.example .env`
4. Run migrations: `python manage.py migrate`
5. Start server: `python manage.py runserver`

## Architecture

[Diagram or explanation of how pieces fit together]

## API Documentation

### GET /api/sessions/
Returns list of user sessions.

**Response:**
```json
{
    "sessions": [
        {
            "id": 1,
            "name": "Session Name",
            "status": "Active"
        }
    ]
}
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test
4. Submit pull request
```

**Documentation checklist:**
- [ ] README explains what the project does
- [ ] Setup instructions are complete
- [ ] API endpoints are documented
- [ ] Architecture is explained
- [ ] Contributing guidelines exist

## 🔄 Phase 6: Continuous Improvement (Making It Better)

### Step 13: Monitoring & Logging
**What we're doing:** Keeping track of how your app behaves
**Like:** Having a dashboard in your car

```python
# Step 13.1: Add logging throughout your code
import logging

logger = logging.getLogger(__name__)

def create_session(user, name):
    """Create a new session"""
    logger.info(f"User {user.username} creating session: {name}")
    
    try:
        session = Session.objects.create(name=name, user=user)
        logger.info(f"Session created successfully: {session.id}")
        return session
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise

# Step 13.2: Configure logging levels
# DEBUG: Detailed information for debugging
# INFO: General information about program execution
# WARNING: Something unexpected happened
# ERROR: Something failed
# CRITICAL: Serious error that might stop the program
```

### Step 14: Performance Optimization
**What we're doing:** Making your app faster and more efficient
**Like:** Tuning a car engine for better performance

```python
# Step 14.1: Database optimization
# Use select_related for foreign keys (reduces database queries)
sessions = Session.objects.select_related('user').all()

# Step 14.2: Caching frequently accessed data
from django.core.cache import cache

def get_user_sessions(user_id):
    cache_key = f'user_sessions_{user_id}'
    sessions = cache.get(cache_key)
    
    if sessions is None:
        sessions = Session.objects.filter(user_id=user_id)
        cache.set(cache_key, sessions, timeout=300)  # 5 minutes
    
    return sessions

# Step 14.3: Frontend optimization
# Load data in background, show loading states
async def load_data_with_feedback(self):
    self.show_loading()
    try:
        data = await self.api_manager.get_data()
        self.update_ui(data)
    finally:
        self.hide_loading()
```

## 🎯 Pro Tips for SUPER Projects

### Code Organization Principles
1. **DRY (Don't Repeat Yourself):** Write reusable functions
2. **SOLID Principles:** Single responsibility, Open/closed, etc.
3. **Separation of Concerns:** Database logic ≠ UI logic ≠ Business logic
4. **Convention over Configuration:** Follow established patterns

### Development Best Practices
1. **Git workflow:** Feature branches, meaningful commits, pull requests
2. **Code reviews:** Always have someone else check your code
3. **Automated testing:** Tests run automatically on every change
4. **Continuous integration:** Automatically test and deploy

### Team Collaboration
1. **Clear documentation:** Future you is a different person
2. **Consistent coding style:** Use formatters and linters
3. **Regular communication:** Daily standups, weekly planning
4. **Knowledge sharing:** Code reviews, pair programming

### Security Considerations
1. **Never commit secrets:** Use environment variables
2. **Validate all inputs:** Don't trust user data
3. **Use HTTPS:** Encrypt data in transit
4. **Keep dependencies updated:** Security patches are important

Remember: **Start simple, iterate quickly, and always prioritize working software over perfect code.** A SUPER project is built through consistent improvement, not perfect initial design!