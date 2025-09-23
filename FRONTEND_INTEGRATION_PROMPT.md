# 🚀 PROMPT PARA IA DEL FRONTEND - SERVAGRO SHIFT SCHEDULER API

## 📋 CONTEXTO

Tienes que integrar una aplicación web frontend con la **SERVAGRO Shift Scheduler API v2.0**. Esta API reemplaza completamente la configuración por Excel y ahora permite configurar turnos desde una interfaz web moderna.

**URL Base de la API:** `https://coral-app-fvng6.ondigitalocean.app/`

## 🎯 OBJETIVO

Crear una interfaz web intuitiva que permita:

1. **Configurar parámetros de optimización** (reemplaza el Excel)
2. **Ejecutar optimización de turnos** con diferentes estrategias
3. **Visualizar resultados** de manera clara y profesional
4. **Manejo de errores** robusto

## 🏗️ ARQUITECTURA DE LA API

### Endpoints Principales:

#### 1. `/config/quick` [POST] - Configuración Rápida
**El más importante - úsalo para configuraciones simples**

```json
// REQUEST:
{
    "posts_count": 5,
    "employees_per_post": 3,
    "comodines_count": 2,
    "base_salary": 1400000,
    "salary_variation": 0.1,
    "year": 2025,
    "month": 8,
    "holidays": ["2025-08-15", "2025-08-20"]
}

// RESPONSE:
{
    "config": { /* Configuración completa generada */ },
    "summary": "Generated config: 5 posts, 15 FIJO employees, 2 COMODINES",
    "employee_count": 17,
    "post_count": 5
}
```

#### 2. `/config/validate` [POST] - Validar Configuración

```json
// REQUEST: OptimizationConfig (ver estructura completa abajo)
// RESPONSE:
{
    "valid": true,
    "errors": [],
    "warnings": ["More than 20 posts may affect performance"],
    "total_posts": 5,
    "total_fijos": 15,
    "total_comodines": 2,
    "estimated_shifts": 310
}
```

#### 3. `/optimize` [POST] - Ejecutar Optimización

```json
// REQUEST:
{
    "config": { /* OptimizationConfig */ },
    "strategy": "lexicographic",  // o "weighted"
    "sunday_strategy": "smart",   // "smart", "balanced", "cost_focused"
    "seed": 42
}

// RESPONSE:
{
    "success": true,
    "message": "Optimization completed successfully. Verification: PASSED",
    "solver_status": "OPTIMAL",
    "solve_time": 2.34,
    "assignments": { "shift_001": "E001", ... },
    "active_employees": ["E001", "E002", ...],
    "employee_metrics": {
        "E001": {
            "emp_id": "E001",
            "salario_contrato": 1400000,
            "hours_assigned": 204,
            "num_sundays": 4,
            "he_hours": 9.15,
            "val_rf": 186349.09,
            "total_employee": 1650000
        }
    },
    "total_metrics": {
        "total_cost": 34568322.53,
        "total_he_hours": 407.55,
        "employees_with_excess_sundays": 13
    }
}
```

#### 4. `/strategies` [GET] - Estrategias Disponibles

```json
{
    "optimization_strategies": {
        "lexicographic": "Multi-level optimization (HE > RF > RN) - Recommended",
        "weighted": "Single weighted objective optimization"
    },
    "sunday_strategies": {
        "smart": "Intelligent Sunday distribution",
        "balanced": "Equal penalty for all employees",
        "cost_focused": "Direct minimization of Sunday costs"
    },
    "recommended": {
        "strategy": "lexicographic",
        "sunday_strategy": "smart"
    }
}
```

## 🎨 INTERFAZ DE USUARIO SUGERIDA

### Paso 1: Configuración Básica (Usar `/config/quick`)
```
┌─────────────────────────────────────┐
│ CONFIGURACIÓN RÁPIDA                │
├─────────────────────────────────────┤
│ Cantidad de puestos: [5        ] ▼ │
│ Empleados por puesto: [3       ] ▼ │  
│ Empleados COMODINES: [2        ] ▼ │
│ Salario base: [$1,400,000     ]    │
│ Variación salarial: [10%      ] ▼ │
│                                     │
│ Año: [2025 ] ▼  Mes: [Agosto  ] ▼ │
│                                     │
│ Festivos:                           │
│ [+ Agregar Fecha] [2025-08-15] ✗   │
│ [+ Agregar Fecha] [2025-08-20] ✗   │
│                                     │
│        [Generar Configuración]      │
└─────────────────────────────────────┘
```

### Paso 2: Configuración Avanzada (Opcional)
Si el usuario quiere más control, mostrar configuración detallada por puesto.

### Paso 3: Estrategias de Optimización
```
┌─────────────────────────────────────┐
│ ESTRATEGIAS DE OPTIMIZACIÓN         │
├─────────────────────────────────────┤
│ Estrategia Principal:               │
│ ○ Lexicográfica (Recomendada)      │
│ ○ Pesos Combinados                  │
│                                     │
│ Estrategia de Domingos:             │
│ ○ Inteligente (Recomendada)         │
│ ○ Balanceada                        │
│ ○ Costo Directo                     │
│                                     │
│ Semilla aleatoria: [42    ]         │
│                                     │
│        [OPTIMIZAR TURNOS]           │
└─────────────────────────────────────┘
```

### Paso 4: Resultados
```
┌─────────────────────────────────────┐
│ RESULTADOS DE OPTIMIZACIÓN          │
├─────────────────────────────────────┤
│ Estado: ✅ OPTIMAL                  │
│ Tiempo: 2.34 segundos               │
│ Empleados activos: 17               │
│ Costo total: $34,568,322            │
│ Horas extra: 407.55h                │
│ Empleados con domingos excesivos: 13│
│                                     │
│ [Ver Detalle] [Exportar] [Nueva]    │
└─────────────────────────────────────┘
```

## 🛠️ FLUJO DE TRABAJO FRONTEND

### 1. Configuración Rápida
```javascript
// Generar configuración desde parámetros simples
const quickConfig = async (params) => {
    const response = await fetch('/config/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
    });
    return await response.json();
};
```

### 2. Validación
```javascript
// Validar antes de optimizar
const validateConfig = async (config) => {
    const response = await fetch('/config/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    return await response.json();
};
```

### 3. Optimización
```javascript
// Ejecutar optimización
const optimize = async (request) => {
    const response = await fetch('/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });
    return await response.json();
};
```

## 📊 ESTRUCTURA DE DATOS COMPLETA

### OptimizationConfig (para configuración detallada):
```typescript
interface OptimizationConfig {
    global_config: {
        year: number;
        month: number;
        hours_per_week: number;
        shift_length_hours: number;
        sunday_threshold: number;
        he_pct: number; // Porcentaje horas extra
        rf_pct: number; // Porcentaje recargo festivo
        rn_pct: number; // Porcentaje recargo nocturno
    };
    holidays: Array<{
        date: string; // "YYYY-MM-DD"
        name: string;
    }>;
    posts_count: number;
    posts_config: Array<{
        post_id: string;
        fixed_employees_count: number;
        employee_salaries: number[];
    }>;
    comodines_count: number;
    comodines_salaries: number[];
}
```

## ⚠️ MANEJO DE ERRORES

### Errores Comunes:
- **400**: Error de validación (mostrar `errors` del response)
- **500**: Error del servidor (mostrar mensaje amigable)
- **Red**: Problemas de conexión

### Validaciones Frontend:
- Mínimo 1 puesto, máximo 20
- Mínimo 1 empleado por puesto, máximo 10
- Salarios entre $500,000 y $10,000,000
- Fechas válidas para festivos

## 🎯 FUNCIONALIDADES CLAVE

### ✅ MUST HAVE:
1. **Configuración rápida** con `/config/quick`
2. **Optimización** con estrategias
3. **Visualización de resultados** básica
4. **Manejo de errores** robusto

### 🎁 NICE TO HAVE:
1. **Configuración detallada** por puesto
2. **Gráficos** de costos y distribución
3. **Comparación** de estrategias
4. **Exportar** resultados
5. **Historial** de optimizaciones

## 🔧 CONFIGURACIÓN RECOMENDADA POR DEFECTO

```javascript
const DEFAULT_CONFIG = {
    posts_count: 5,
    employees_per_post: 3,
    comodines_count: 2,
    base_salary: 1400000,
    salary_variation: 0.1,
    year: 2025,
    month: 8,
    holidays: []
};

const DEFAULT_OPTIMIZATION = {
    strategy: "lexicographic",
    sunday_strategy: "smart", 
    seed: 42
};
```

## 🚀 COMANDOS DE PRUEBA (para desarrollo)

```bash
# Probar configuración rápida
curl -X POST "http://localhost:8001/config/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "posts_count": 3,
    "employees_per_post": 3,
    "comodines_count": 2,
    "base_salary": 1400000,
    "salary_variation": 0.1,
    "year": 2025,
    "month": 8
  }'

# Ver estrategias disponibles
curl "http://localhost:8001/strategies"

# Ver ejemplo de configuración
curl "http://localhost:8001/config/example"
```

## 📱 UX/UI GUIDELINES

- **Simple primero**: Empezar con configuración rápida
- **Progresivo**: Opción para configuración avanzada
- **Visual**: Mostrar progreso durante optimización
- **Claro**: Resultados fáciles de entender
- **Responsivo**: Funcionar en móviles y desktop

¡La API está lista y funcionando! Tu trabajo es crear una interfaz intuitiva que haga que configurar y optimizar turnos sea súper fácil para el usuario final.

## 🔗 ENLACES ÚTILES

- **API Docs**: `http://localhost:8001/docs` (Swagger/OpenAPI)
- **API Health**: `http://localhost:8001/health`
- **Estrategias**: `http://localhost:8001/strategies`

¡A programar! 🚀