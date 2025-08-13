# Documentação da API - PerPlan.tech

## Visão Geral

A API do PerPlan.tech é uma API REST desenvolvida em Django que gerencia um sistema de contagem de tráfego veicular. O sistema oferece autenticação JWT, gerenciamento de usuários, sessões de contagem, trabalhos (projetos), padrões de contagem e sistema de tickets.

**Base URL:** `http://localhost:8000` (desenvolvimento)

## Autenticação

### Tipo de Autenticação
- **JWT (JSON Web Tokens)** usando `rest_framework_simplejwt`
- Header de autorização: `Authorization: Bearer <access_token>`

### Endpoints de Autenticação

#### POST `/auth/login/`
Realiza login e retorna tokens JWT.

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response (200 OK):**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "usuario",
        "name": "Nome",
        "last_name": "Sobrenome",
        "email": "email@exemplo.com",
        "setor": "CON"
    }
}
```

**Response (401 Unauthorized):**
```json
{
    "detail": "Credenciais inválidas!"
}
```

#### POST `/auth/register/`
Registra um novo usuário.

**Request Body:**
```json
{
    "username": "string",
    "password1": "string",
    "password2": "string",
    "name": "string",
    "last_name": "string",
    "email": "string",
    "setor": "CON"
}
```

**Setores válidos:**
- `CON` - Contagem
- `DIG` - Digitação  
- `P&D` - Perci
- `SUPER` - Supervisão
- `ENG` - Engenharia
- `ADM` - Administrativo

#### POST `/auth/token/`
Obter token JWT (alternativo ao login).

#### POST `/auth/token/refresh/`
Renovar access token usando refresh token.

#### POST `/auth/api/token/`
Gerar token para usuário já autenticado na sessão.

#### GET `/auth/check-auth/`
Verificar se o usuário está autenticado.

---

## Módulos da API

### 1. Contagens (`/contagens/`)

Gerenciamento de sessões de contagem de tráfego.

#### GET `/contagens/`
Lista todas as sessões de contagem.

**Response:**
```json
[
    {
        "id": 1,
        "sessao": "SESS_001",
        "pesquisador": "João Silva",
        "codigo": "PRJ001",
        "ponto": "Ponto A",
        "horario_inicio": "08:00",
        "horario_fim": "17:00",
        "data": "2023-12-01",
        "status": "Em andamento",
        "padrao": "padrao_perplan",
        "movimentos": [...],
        "created_at": "2023-12-01T08:00:00Z",
        "updated_at": "2023-12-01T17:00:00Z"
    }
]
```

#### GET `/contagens/detalhes/<int:sessao_id>/`
Detalhes de uma sessão específica.

#### POST `/contagens/registrar-sessao/`
Registra uma nova sessão de contagem.

**Request Body:**
```json
{
    "sessao": "SESS_002",
    "pesquisador": "Maria Santos",
    "codigo": "PRJ001",
    "ponto": "Ponto B",
    "horario_inicio": "08:00",
    "horario_fim": "17:00",
    "data": "2023-12-02",
    "padrao": "padrao_perplan",
    "movimentos": []
}
```

#### POST `/contagens/finalizar-sessao/`
Finaliza uma sessão ativa.

#### POST `/contagens/finalizar-por-nome/`
Finaliza sessão por nome.

#### POST `/contagens/atualizar-contagens/`
Atualiza contagens de uma sessão.

#### GET `/contagens/get/`
Obtém contagens com filtros.

#### GET `/contagens/exportar-csv/<int:sessao_id>`
Exporta sessão para CSV.

#### POST `/contagens/buscar-sessao/`
Busca sessão por critérios.

#### GET `/contagens/api/pontos-por-codigo/`
Retorna pontos filtrados por código.

---

### 2. Trabalhos (`/trabalhos/`)

Gerenciamento da hierarquia Cliente → Código → Ponto.

#### Clientes

##### GET `/trabalhos/api/clientes/`
Lista todos os clientes.

**Response:**
```json
[
    {
        "id": 1,
        "nome": "Cliente Exemplo Ltda"
    }
]
```

##### POST `/trabalhos/api/clientes/`
Cria novo cliente.

**Request Body:**
```json
{
    "nome": "Novo Cliente Ltda"
}
```

##### PUT `/trabalhos/api/clientes/<id>/`
Atualiza cliente.

##### DELETE `/trabalhos/api/clientes/<id>/`
Remove cliente.

#### Códigos

##### GET `/trabalhos/api/codigos/`
Lista todos os códigos.

**Response:**
```json
[
    {
        "id": 1,
        "cliente": 1,
        "codigo": "PRJ001",
        "descricao": "Projeto de contagem rodoviária"
    }
]
```

##### POST `/trabalhos/api/codigos/`
Cria novo código.

**Request Body:**
```json
{
    "cliente": 1,
    "codigo": "PRJ002",
    "descricao": "Novo projeto"
}
```

#### Pontos

##### GET `/trabalhos/api/pontos/`
Lista todos os pontos.

**Response:**
```json
[
    {
        "id": 1,
        "codigo": 1,
        "nome": "Ponto A",
        "localizacao": "Rua Principal, 123"
    }
]
```

##### POST `/trabalhos/api/pontos/`
Cria novo ponto.

##### POST `/trabalhos/api/pontos/bulk-create/`
Criação em lote de pontos.

**Request Body:**
```json
{
    "codigo_id": 1,
    "pontos": [
        {
            "nome": "Ponto 1",
            "localizacao": "Local 1"
        },
        {
            "nome": "Ponto 2", 
            "localizacao": "Local 2"
        }
    ]
}
```

---

### 3. Padrões (`/padroes/`)

Gerenciamento de padrões de contagem e configurações do usuário.

#### GET `/padroes/api/padroes-api/`
Lista padrões de contagem globais.

**Response:**
```json
[
    {
        "id": 1,
        "pattern_type": "padrao_perplan",
        "veiculo": "Carro",
        "bind": "C",
        "order": 1
    }
]
```

#### GET `/padroes/api/user-padroes/`
Lista padrões personalizados do usuário autenticado.

#### POST `/padroes/api/user-padroes/`
Cria padrão personalizado para o usuário.

**Request Body:**
```json
{
    "pattern_type": "padrao_personalizado",
    "veiculo": "Motocicleta",
    "bind": "M"
}
```

#### GET `/padroes/user/info/`
Informações do usuário autenticado.

**Response:**
```json
{
    "id": 1,
    "username": "usuario",
    "name": "Nome",
    "last_name": "Sobrenome",
    "email": "email@exemplo.com",
    "setor": "CON",
    "preferences": {}
}
```

#### GET `/padroes/user/preferences/`
Preferências do usuário.

#### POST `/padroes/user/preferences/update/`
Atualiza preferências do usuário.

#### GET `/padroes/tipos-de-padrao/`
Lista tipos de padrão disponíveis.

#### GET `/padroes/padroes-globais/`
Lista padrões globais do sistema.

#### GET `/padroes/merged-binds/`
Retorna padrões mesclados (globais + personalizados do usuário).

#### POST `/padroes/padroes/reorder/`
Reordena padrões.

---

### 4. Tickets (`/tickets/`)

Sistema de gerenciamento de tarefas/tickets.

#### GET `/tickets/api/`
Lista todos os tickets.

**Response:**
```json
[
    {
        "id": 1,
        "turno": "MANHA",
        "coordenador": 1,
        "codigo": 1,
        "cam": "CAM001",
        "mov": "MOV001", 
        "padrao": 1,
        "duracao": "8.50",
        "periodo_inicio": "08:00:00",
        "periodo_fim": "16:30:00",
        "data": "2023-12-01",
        "nivel": 5,
        "prioridade": "MEDIA",
        "status": "AGUARDANDO",
        "pesquisador": null,
        "observacao": "",
        "criado_em": "2023-12-01T08:00:00Z"
    }
]
```

#### POST `/tickets/api/`
Cria novo ticket.

**Request Body:**
```json
{
    "turno": "MANHA",
    "coordenador": 1,
    "codigo": 1,
    "cam": "CAM002",
    "mov": "MOV002",
    "padrao": 1,
    "duracao": "4.25",
    "periodo_inicio": "08:00:00",
    "periodo_fim": "12:15:00",
    "data": "2023-12-02",
    "nivel": 3,
    "prioridade": "ALTA",
    "observacao": "Observação importante"
}
```

**Status possíveis:**
- `AGUARDANDO` - Aguardando
- `INICIADO` - Iniciado
- `CONTANDO` - Contando
- `PAUSADO` - Pausado
- `FINALIZADO` - Finalizado

**Prioridades:**
- `BAIXA` - Baixa
- `MEDIA` - Média
- `ALTA` - Alta
- `URGENTE` - Urgente

#### POST `/tickets/<id>/change-status/`
Altera status do ticket.

#### POST `/tickets/<id>/atribuir-pesquisador/`
Atribui pesquisador ao ticket.

#### GET `/tickets/api/codigos/`
Lista códigos para autocomplete.

#### GET `/tickets/api/padroes/`
Lista padrões para autocomplete.

#### GET `/tickets/api/pesquisadores/`
Lista pesquisadores para autocomplete.

---

### 5. Updates (`/updates/`)

Sistema de versionamento e atualizações.

#### GET `/updates/api/check-version/`
Verifica versão mais recente disponível.

**Response:**
```json
{
    "latest_version": "1.2.0",
    "changelog": "- Correção de bugs\n- Novas funcionalidades",
    "download_url": "/updates/api/download/"
}
```

#### GET `/updates/api/download/`
Download da versão mais recente.

#### GET `/updates/api/history/`
Histórico de versões.

**Response:**
```json
[
    {
        "version": "1.2.0",
        "changelog": "Correções e melhorias",
        "published_at": "2023-12-01T10:00:00Z"
    }
]
```

#### POST `/updates/api/upload/` *(Staff apenas)*
Upload de nova versão.

---

## Modelos de Dados

### User (Usuário)
```python
{
    "id": "integer",
    "username": "string (unique)",
    "name": "string",
    "last_name": "string", 
    "email": "string (unique)",
    "setor": "string (CON|DIG|P&D|SUPER|ENG|ADM)",
    "preferences": "object (JSON)"
}
```

### Session (Sessão)
```python
{
    "id": "integer",
    "sessao": "string (unique)",
    "pesquisador": "string",
    "codigo": "string",
    "ponto": "string",
    "horario_inicio": "string (HH:MM)",
    "horario_fim": "string (HH:MM)",
    "data": "string (YYYY-MM-DD)",
    "status": "string (Aguardando|Em andamento|Concluída)",
    "padrao": "string",
    "movimentos": "array (JSON)",
    "criado_por": "integer (User FK)",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

### Cliente
```python
{
    "id": "integer",
    "nome": "string (unique)"
}
```

### Codigo
```python
{
    "id": "integer",
    "cliente": "integer (Cliente FK)",
    "codigo": "string",
    "descricao": "string"
}
```

### Ponto
```python
{
    "id": "integer", 
    "codigo": "integer (Codigo FK)",
    "nome": "string",
    "localizacao": "string"
}
```

### PadraoContagem
```python
{
    "id": "integer",
    "pattern_type": "string",
    "veiculo": "string",
    "bind": "string",
    "order": "integer"
}
```

### Ticket
```python
{
    "id": "integer",
    "turno": "string (MANHA|NOITE)",
    "coordenador": "integer (User FK)",
    "codigo": "integer (Codigo FK)",
    "cam": "string",
    "mov": "string",
    "padrao": "integer (PadraoContagem FK)",
    "duracao": "decimal",
    "periodo_inicio": "time",
    "periodo_fim": "time",
    "data": "date",
    "nivel": "integer (1-10)",
    "prioridade": "string (BAIXA|MEDIA|ALTA|URGENTE)",
    "status": "string (AGUARDANDO|INICIADO|CONTANDO|PAUSADO|FINALIZADO)",
    "pesquisador": "integer (User FK, nullable)",
    "observacao": "text",
    "criado_em": "datetime",
    "atualizado_em": "datetime"
}
```

---

## Códigos de Status HTTP

### Sucesso
- `200 OK` - Requisição bem-sucedida
- `201 Created` - Recurso criado com sucesso
- `204 No Content` - Requisição bem-sucedida sem conteúdo de retorno

### Erro do Cliente  
- `400 Bad Request` - Dados inválidos na requisição
- `401 Unauthorized` - Token JWT inválido ou ausente
- `403 Forbidden` - Permissão insuficiente 
- `404 Not Found` - Recurso não encontrado

### Erro do Servidor
- `500 Internal Server Error` - Erro interno do servidor

---

## Permissões e Roles

### Setores e Permissões
- **CON (Contagem)**: Acesso a funcionalidades de contagem
- **DIG (Digitação)**: Acesso a funcionalidades de digitação
- **P&D (Perci)**: Acesso a pesquisa e desenvolvimento
- **SUPER (Supervisão)**: Permissões de supervisão, pode coordenar tickets
- **ENG (Engenharia)**: Acesso a funcionalidades de engenharia
- **ADM (Administrativo)**: Acesso administrativo completo

### Autenticação Obrigatória
Todos os endpoints requerem autenticação JWT, exceto:
- `/auth/login/`
- `/auth/register/`
- `/auth/token/`
- `/updates/api/check-version/`
- `/updates/api/download/`
- `/updates/api/history/`

---

## Filtros e Paginação

### Filtros Comuns
A maioria dos endpoints de listagem suporta filtros via query parameters:

```
GET /contagens/?status=Em%20andamento
GET /tickets/api/?prioridade=ALTA&status=AGUARDANDO
GET /trabalhos/api/pontos/?codigo=1
```

### Ordenação
Use o parâmetro `ordering`:

```
GET /tickets/api/?ordering=-criado_em
GET /contagens/?ordering=data
```

---

## Exemplos de Uso

### Fluxo de Autenticação
```javascript
// 1. Login
const loginResponse = await fetch('/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user', password: 'pass' })
});
const { access, refresh } = await loginResponse.json();

// 2. Usar token nas requisições
const response = await fetch('/contagens/', {
    headers: { 'Authorization': `Bearer ${access}` }
});
```

### Criar Sessão de Contagem
```javascript
const session = await fetch('/contagens/registrar-sessao/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        sessao: 'SESS_003',
        pesquisador: 'Ana Costa',
        codigo: 'PRJ001',
        ponto: 'Ponto C',
        horario_inicio: '09:00',
        horario_fim: '18:00',
        data: '2023-12-03',
        padrao: 'padrao_perplan'
    })
});
```

### Criar Ticket
```javascript
const ticket = await fetch('/tickets/api/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        turno: 'MANHA',
        coordenador: 1,
        codigo: 1,
        cam: 'CAM003',
        mov: 'MOV003',
        padrao: 1,
        duracao: 6.00,
        periodo_inicio: '08:00:00',
        periodo_fim: '14:00:00',
        data: '2023-12-04',
        nivel: 4,
        prioridade: 'MEDIA'
    })
});
```

---

## Observações Técnicas

### Tecnologias Utilizadas
- **Django 5.1.3** - Framework web
- **Django REST Framework** - API REST
- **SimpleJWT** - Autenticação JWT
- **PostgreSQL** - Banco de dados principal
- **CORS Headers** - Suporte a CORS

### Configurações de CORS
A API está configurada para aceitar requisições de qualquer origem durante desenvolvimento (`ALLOWED_HOSTS = ['*']`).

### Logs
O sistema mantém logs das operações principais para auditoria e debugging.

### Uploads
Suporte a upload de arquivos para:
- Imagens de detalhes de pontos (`/media/ponto_details/`)
- Arquivos de atualização (`/media/updates/`)

---

*Documentação gerada automaticamente a partir do código fonte - PerPlan.tech*