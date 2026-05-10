# Plan de desarrollo - Libro de Caja

## Objetivo

Desarrollar una aplicacion web de libro de caja basico para registrar entradas y retiradas de dinero en dos cuentas:

- Efectivo
- Tarjeta

La aplicacion debe mantener actualizado el saldo de cada cuenta, permitir consultar movimientos y ofrecer opciones para imprimir, exportar a PDF o enviar reportes por email.

## Stack tecnico requerido

- Base de datos: MySQL
- Backend: Python
- API: REST
- Frontend: React
- Contenedores: Docker y Docker Compose

Stack recomendado:

- Backend: FastAPI
- ORM: SQLAlchemy
- Migraciones: Alembic
- Validacion: Pydantic
- Frontend: React con Vite
- Estilos: CSS modular o Tailwind, segun se decida en la implementacion
- Email: SMTP configurable por variables de entorno
- PDF: generacion desde backend o frontend, manteniendo una salida imprimible consistente

## Estructura esperada del proyecto

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── main.jsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Modelo funcional

### Cuentas

La aplicacion debe tener dos cuentas fijas:

- `cash`: efectivo
- `card`: tarjeta

Cada movimiento pertenece a una cuenta. El saldo de cada cuenta se calcula con la suma de ingresos menos retiradas.

### Movimientos

Un movimiento puede ser:

- Entrada de dinero
- Retirada de dinero

Campos obligatorios:

- Nombre o empresa
- Concepto
- Cuenta: efectivo o tarjeta
- Tipo: entrada o retirada
- Cantidad de dinero
- Fecha

Campos recomendados:

- Notas opcionales
- Usuario creador, si en el futuro se anade autenticacion
- Fecha de creacion
- Fecha de modificacion

### Personas o empresas

El campo `nombre o empresa` debe guardarse en una tabla independiente para poder reutilizarlo en nuevos movimientos.

Requisitos:

- Crear nuevas personas/empresas desde el formulario de movimientos si no existen.
- Permitir busqueda/autocompletado.
- Evitar duplicados obvios por nombre normalizado.

### Conceptos

El campo `concepto` debe guardarse en otra tabla independiente.

Requisitos:

- Crear nuevos conceptos desde el formulario de movimientos si no existen.
- Permitir busqueda/autocompletado.
- Evitar duplicados obvios por texto normalizado.

## Modelo de base de datos

### Tabla `accounts`

```text
id
code
name
created_at
```

Registros iniciales:

```text
cash | Efectivo
card | Tarjeta
```

### Tabla `counterparties`

Personas, clientes, proveedores o empresas usadas en los movimientos.

```text
id
name
normalized_name
created_at
updated_at
```

### Tabla `concepts`

Conceptos usados en los movimientos.

```text
id
name
normalized_name
created_at
updated_at
```

### Tabla `transactions`

```text
id
account_id
counterparty_id
concept_id
type
amount
transaction_date
notes
created_at
updated_at
```

Restricciones:

- `type` solo puede ser `income` o `expense`.
- `amount` debe ser mayor que 0.
- El saldo no se guarda como valor manual editable; se calcula desde movimientos.

## API backend

### Salud del sistema

- `GET /health`

### Cuentas y saldos

- `GET /accounts`
- `GET /accounts/balances`

Respuesta esperada de saldos:

```json
{
  "cash": {
    "name": "Efectivo",
    "balance": 1250.5
  },
  "card": {
    "name": "Tarjeta",
    "balance": 430.0
  }
}
```

### Movimientos

- `GET /transactions`
- `POST /transactions`
- `GET /transactions/{id}`
- `PUT /transactions/{id}`
- `DELETE /transactions/{id}`

Filtros recomendados en `GET /transactions`:

- Fecha desde
- Fecha hasta
- Cuenta
- Tipo
- Nombre/empresa
- Concepto

### Personas o empresas

- `GET /counterparties`
- `POST /counterparties`
- `PUT /counterparties/{id}`
- `DELETE /counterparties/{id}`

### Conceptos

- `GET /concepts`
- `POST /concepts`
- `PUT /concepts/{id}`
- `DELETE /concepts/{id}`

### Reportes

- `GET /reports/cashbook`
- `GET /reports/cashbook/pdf`
- `POST /reports/cashbook/email`

El reporte debe poder filtrarse por fechas y por cuenta.

## Frontend React

### Pantallas principales

1. Dashboard
   - Mostrar saldo actual de efectivo.
   - Mostrar saldo actual de tarjeta.
   - Mostrar total combinado.
   - Accesos rapidos para crear entrada o retirada.

2. Libro de caja
   - Tabla de movimientos.
   - Filtros por fecha, cuenta, tipo, nombre/empresa y concepto.
   - Acciones para editar o eliminar movimientos.
   - Botones para imprimir, exportar a PDF y enviar por email.

3. Formulario de movimiento
   - Tipo: entrada o retirada.
   - Cuenta: efectivo o tarjeta.
   - Nombre o empresa con autocompletado.
   - Concepto con autocompletado.
   - Cantidad.
   - Fecha.
   - Notas opcionales.

4. Gestion de nombres/empresas
   - Listar, crear, editar y eliminar.

5. Gestion de conceptos
   - Listar, crear, editar y eliminar.

### Requisitos de interfaz

- El usuario debe ver siempre los saldos actualizados despues de crear, editar o eliminar un movimiento.
- Las cantidades deben mostrarse con formato de moneda.
- Las retiradas deben diferenciarse visualmente de las entradas.
- La vista de impresion debe ser limpia y sin controles innecesarios.
- El envio por email debe solicitar destinatario y, opcionalmente, asunto/mensaje.

## Docker

El proyecto debe levantarse con:

```bash
docker compose up --build
```

Servicios esperados:

- `mysql`
- `backend`
- `frontend`

Variables recomendadas:

```text
MYSQL_DATABASE=libro_caja
MYSQL_USER=libro_caja_user
MYSQL_PASSWORD=change_me
MYSQL_ROOT_PASSWORD=change_me_root

DATABASE_URL=mysql+pymysql://libro_caja_user:change_me@mysql:3306/libro_caja

BACKEND_PORT=8000
FRONTEND_PORT=5173

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

## Fases de desarrollo

### Fase 1 - Base del proyecto

- Crear estructura `backend/`, `frontend/` y archivos Docker.
- Crear `docker-compose.yml`.
- Crear `.env.example`.
- Confirmar que MySQL, backend y frontend arrancan juntos.
- Anadir endpoint `GET /health`.

Criterio de aceptacion:

- `docker compose up --build` levanta todos los servicios.
- El backend responde correctamente en `/health`.
- El frontend muestra una pantalla inicial.

### Fase 2 - Base de datos y modelos

- Configurar SQLAlchemy.
- Configurar Alembic.
- Crear modelos:
  - `Account`
  - `Counterparty`
  - `Concept`
  - `Transaction`
- Crear migraciones iniciales.
- Insertar cuentas iniciales: efectivo y tarjeta.

Criterio de aceptacion:

- Las tablas se crean correctamente en MySQL.
- Existen las dos cuentas base.

### Fase 3 - API de movimientos y saldos

- Implementar CRUD de movimientos.
- Implementar calculo de saldos por cuenta.
- Implementar validaciones de cantidad, tipo y cuenta.
- Implementar filtros basicos de movimientos.

Criterio de aceptacion:

- Crear una entrada aumenta el saldo de la cuenta seleccionada.
- Crear una retirada reduce el saldo de la cuenta seleccionada.
- Editar o eliminar movimientos recalcula correctamente los saldos.

### Fase 4 - API de nombres/empresas y conceptos

- Implementar CRUD de personas/empresas.
- Implementar CRUD de conceptos.
- Implementar busqueda para autocompletado.
- Permitir crear registros desde el flujo de movimientos.

Criterio de aceptacion:

- Los movimientos referencian registros existentes en tablas independientes.
- El frontend puede buscar y reutilizar nombres/empresas y conceptos.

### Fase 5 - Frontend principal

- Crear dashboard de saldos.
- Crear tabla de movimientos con filtros.
- Crear formulario para entradas y retiradas.
- Conectar frontend con backend.
- Actualizar saldos despues de cada operacion.

Criterio de aceptacion:

- El usuario puede gestionar movimientos desde la interfaz.
- Los saldos se ven correctamente y se actualizan sin recargar manualmente.

### Fase 6 - Impresion y PDF

- Crear vista imprimible del libro de caja.
- Implementar accion de imprimir desde frontend.
- Implementar exportacion a PDF.
- Asegurar que el PDF respeta filtros de fecha y cuenta.

Criterio de aceptacion:

- El usuario puede imprimir el listado actual.
- El usuario puede descargar un PDF del reporte filtrado.

### Fase 7 - Envio por email

- Configurar servicio SMTP en backend.
- Crear endpoint para enviar reporte por email.
- Permitir introducir destinatario desde frontend.
- Adjuntar PDF o incluir resumen en el cuerpo del email.

Criterio de aceptacion:

- Con variables SMTP validas, el sistema envia el reporte por email.
- Si SMTP no esta configurado, el usuario recibe un error claro.

### Fase 8 - Calidad y documentacion

- Anadir README con instrucciones de instalacion y uso.
- Anadir datos de ejemplo opcionales.
- Anadir pruebas basicas del backend.
- Revisar validaciones y mensajes de error.
- Revisar responsividad del frontend.

Criterio de aceptacion:

- Una persona nueva puede levantar el proyecto siguiendo el README.
- Las pruebas basicas pasan.
- La aplicacion cubre el flujo completo: crear movimientos, consultar saldos, imprimir, exportar PDF y enviar email.

## Consideraciones importantes

- Usar importes con tipo decimal, no float, para evitar errores de precision monetaria.
- Guardar siempre cantidades positivas y usar el campo `type` para determinar si suma o resta.
- Los saldos deben calcularse desde los movimientos para evitar inconsistencias.
- Las eliminaciones pueden ser fisicas en la primera version, pero conviene considerar borrado logico en una fase futura.
- La aplicacion debe estar preparada para anadir autenticacion mas adelante, aunque no sea obligatoria en la primera version.

## Fuera de alcance inicial

- Autenticacion de usuarios.
- Roles y permisos.
- Multiempresa.
- Conciliacion bancaria.
- Importacion desde Excel o CSV.
- Auditoria avanzada.

Estos puntos pueden anadirse en versiones posteriores.
