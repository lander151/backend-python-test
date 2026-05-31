# Notification Service

Servicio intermediario de notificaciones construido con **FastAPI**. Recibe solicitudes de notificación de los clientes, las persiste en memoria y las delega de forma asíncrona a un provider externo.

---

## Arranque rápido

```bash
# 1. Levantar infraestructura
docker-compose up -d provider influxdb grafana

# 2. Levantar la app
docker-compose up -d --build app

# 3. Ejecutar los tests de carga
docker-compose run --rm load-test

# 4. Ver resultados
# http://localhost:3000/d/backend-performance-scorecard/
```

---

## API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/v1/requests` | Registra una nueva solicitud → devuelve `{"id": "..."}` |
| `POST` | `/v1/requests/{id}/process` | Lanza el envío al provider en background |
| `GET` | `/v1/requests/{id}` | Consulta el estado de la solicitud |

La documentación interactiva está disponible en `http://localhost:5000/docs`.

---

## Estructura del Proyecto

```
app/
├── main.py              # Aplicación FastAPI con endpoints
├── models.py            # Modelos Pydantic
├── database.py          # Gestión de base de datos
├── provider.py          # Integración con el proveedor externo
├── settings.py          # Configuración centralizada
├── constants.py         # Constantes del proyecto
├── .env-example         # Template de variables de entorno
├── pyproject.toml       # Configuración de dependencias (uv)
├── uv.lock              # Lock file de dependencias
└── routers/
    ├── __init__.py
    └── requests.py      # Endpoints /v1/requests
└── Dockerfile           # Construcción del contenedor
```

---

## Pipeline de Procesamiento

El endpoint `POST /v1/requests/{id}/process` está diseñado para **no bloquear al cliente**.

En lugar de esperar la respuesta del provider, delega el envío a un `BackgroundTask` de FastAPI y devuelve `202 Accepted` inmediatamente:

```python
background_tasks.add_task(call_provider, request_id, notification)
return {"status": "processing", "id": request_id}
```

Mientras el cliente ya tiene su respuesta, el pipeline continúa en background:

```
POST /process → 202 Accepted (inmediato)
                    ↓
             call_provider() en background
                    ↓
             Reintento 1 → falla → espera 1s
             Reintento 2 → falla → espera 2s
             Reintento 3 → éxito → status: "sent"
                    ↓
             GET /requests/{id} → {"status": "sent"}
```

El ciclo de vida completo de una notificación es:

```
queued → processing → sent
                    ↘ failed
```

### Reintentos con backoff exponencial

Los reintentos usan **backoff exponencial** — cada intento fallido espera el doble que el anterior (`RETRY_BACKOFF ** attempt`), reduciendo la presión sobre el provider en momentos de sobrecarga. Esto tolera fallos transitorios sin propagar errores al cliente:

- **Red inestable:** el provider puede tener latencia temporal
- **Fallos transitorios:** timeouts o rate limits que se recuperan rápidamente

El número de reintentos y el backoff son configurables via `.env`.

---

## Configuración

### Gestión de Dependencias: `uv`

La aplicación usa **[uv](https://docs.astral.sh/uv/)** en lugar de pip:
- **Velocidad:** resolución de dependencias más rápida
- **Fiabilidad:** lock file determinista
- **Dockerfile simplificado:** imagen base con uv preinstalado

### Settings (`settings.py`)

Configuración centralizada con valores por defecto válidos para el entorno de evaluación:

```python
class Settings(BaseSettings):
    # App
    app_name: str = "Notification Service"
    app_version: str = "1.0.0"
    debug: bool = False
    port: int = 5000

    # Provider
    provider_url: str = "http://provider:3001"
    provider_api_key: str = "test-dev-2026"
    provider_timeout: float = 10.0

    # Reintentos
    max_retries: int = 3
    retry_backoff: float = 1.0
```

> ⚠️ **Nota:** Por ser una prueba sin credenciales reales, los valores están configurados por defecto para facilitar la ejecución. En producción deben venir exclusivamente de variables de entorno.

### Variables de Entorno (`.env-example`)

```env
PROVIDER_URL=provider-url
PROVIDER_API_KEY=api-key
PROVIDER_TIMEOUT=10.0
MAX_RETRIES=3
```

Copiar a `.env` y actualizar con valores reales según el entorno.

---

## Base de Datos en Memoria

No se requería persistencia, por lo que se usa un **dict de Python** como store:

```python
notifications_db: dict[str, NotificationRequest] = {}
```

El acceso está protegido con `asyncio.Lock()` para evitar race conditions bajo carga concurrente. En producción, reemplazar con Redis o PostgreSQL según el requisito de persistencia.