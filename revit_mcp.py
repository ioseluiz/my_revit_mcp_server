from fastmcp import FastMCP
import httpx
from typing import List, Dict, Any

# Inicializamos el servidor
mcp = FastMCP("INIO Revit 2025 Assistant")

# IMPORTANTE: Esta es la URL exacta que definimos en el C# (ServerController.cs)
# Nota la barra al final y que dice 'mcp', no 'api'
REVIT_BRIDGE_URL = "http://localhost:5000/mcp/"


@mcp.tool()
async def obtener_elementos_con_datos(tipo_elemento: str) -> str:
    """
    Obtiene elementos del modelo incluyendo sus parámetros de gestión de obra.
    Busca: codigo_cronograma, codigo_actividad, costo_unitario, division, master format.
    
    Args:
        tipo_elemento: 'columnas', 'cimentacion', 'vigas', 'pisos', 'muros', 'puertas', 'ventanas'.
    """
    
    # 1. Definir qué categoría de Revit queremos
    mapa_categorias = {
        "columnas": "OST_StructuralColumns",
        "cimentacion": "OST_StructuralFoundation",
        "vigas": "OST_StructuralFraming",
        "pisos": "OST_Floors",
        "muros": "OST_Walls",
        "puertas": "OST_Doors",
        "ventanas": "OST_Windows"
    }
    
    clave = tipo_elemento.lower()
    if clave not in mapa_categorias:
        return f"Error: Categoría '{tipo_elemento}' no configurada."

    categoria_tecnica = mapa_categorias[clave]

    # 2. Definir qué parámetros queremos leer (Exactamente como se llaman en Revit)
    # Nota: Revit es sensible a mayúsculas/minúsculas. Asegúrate de escribirlos bien.
    parametros_a_buscar = [
        "codigo_cronograma", 
        "codigo_actividad", 
        "costo_unitario", 
        "division", 
        "master format",
        "Assembly Code",  # A veces el MasterFormat nativo se llama así en inglés
        "Keynote"         # Otro común para códigos
    ]

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "get_elements_with_params", # Nuevo comando en C#
                "Payload": {
                    "category": categoria_tecnica,
                    "parameters": parametros_a_buscar
                }
            }
            
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=60.0) # Timeout más largo por si son muchos datos
            resp.raise_for_status()
            
            # Procesar un poco la respuesta para Claude
            data = resp.json()
            
            # Filtramos para mostrar solo elementos que tengan ALGUN dato relevante (opcional)
            # Para no llenar el chat de elementos vacíos si hay miles.
            elementos_con_datos = []
            for item in data:
                # Chequeamos si alguno de los parámetros importantes tiene valor
                tiene_dato = any(item.get(p) for p in parametros_a_buscar)
                if tiene_dato:
                    elementos_con_datos.append(item)
            
            if not elementos_con_datos:
                return f"Se encontraron {len(data)} elementos de tipo '{tipo_elemento}', pero ninguno tiene los parámetros solicitados ({', '.join(parametros_a_buscar)}) rellenos."
                
            return f"Se encontraron {len(elementos_con_datos)} elementos con datos relevantes (mostrando muestra):\n{str(elementos_con_datos[:20])} \n...(y más)"

    except Exception as e:
        return f"Error obteniendo datos: {str(e)}"

@mcp.tool()
async def obtener_info_proyecto() -> str:
    """
    Obtiene información general del proyecto de Revit abierto actualmente.
    Retorna detalles como nombre del archivo, ubicación y usuario.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Estructura que espera el C# (McpRequest)
            payload = {
                "Command": "get_project_info",  # Debe coincidir con el switch en McpRequestHandler.cs
                "Payload": {}                   # Payload vacío porque no requiere argumentos
            }
            
            # En C# usamos HttpListener que recibe POST en la raiz del contexto
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=10.0)
            
            # Si el servidor C# devuelve 500 o 404, esto lanzará error
            resp.raise_for_status()
            
            return resp.text
    except Exception as e:
        return f"Error conectando con Revit: {str(e)}. Asegúrate de que el botón en Revit esté en (ON)."

@mcp.tool()
async def listar_muros() -> str:
    """
    Lista los muros en el modelo actual.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "get_walls", # Debe coincidir con el switch en McpRequestHandler.cs
                "Payload": {}
            }
            
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=30.0)
            resp.raise_for_status()
            
            return resp.text
    except Exception as e:
        return f"Error obteniendo muros: {str(e)}"
    

@mcp.tool()
async def listar_elementos_estructurales(tipo_elemento: str) -> str:
    """
    Lista elementos estructurales del modelo.
    
    Args:
        tipo_elemento: El tipo de elemento a buscar. Opciones válidas:
                       'columnas' (para Structural Columns),
                       'cimentacion' (para Structural Foundations),
                       'vigas' (para Structural Framing),
                       'pisos' (para Floors).
    """
    # Mapeo de lenguaje natural a lenguaje técnico de Revit (BuiltInCategory)
    mapa_categorias = {
        "columnas": "OST_StructuralColumns",
        "cimentacion": "OST_StructuralFoundation",
        "vigas": "OST_StructuralFraming",
        "pisos": "OST_Floors",
        "muros": "OST_Walls"
    }
    
    # Normalizamos la entrada (minusculas)
    clave = tipo_elemento.lower()
    
    if clave not in mapa_categorias:
        return f"Error: Tipo '{tipo_elemento}' no soportado. Usa: columnas, cimentacion, vigas, pisos."

    categoria_tecnica = mapa_categorias[clave]

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "get_elements_by_category",
                "Payload": {
                    "category": categoria_tecnica
                }
            }
            
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=30.0)
            resp.raise_for_status()
            
            # Si la respuesta es muy larga, Claude puede cortarse. 
            # Devolvemos un resumen si hay demasiados elementos, o el JSON directo.
            data = resp.json()
            cantidad = len(data)
            return f"Se encontraron {cantidad} elementos de tipo '{tipo_elemento}':\n{resp.text}"

    except Exception as e:
        return f"Error obteniendo elementos: {str(e)}"
    

@mcp.tool()
async def calcular_volumen_concreto(elementos: List[str]) -> str:
    """
    Calcula el volumen total de concreto (hormigón) en metros cúbicos para las categorías solicitadas.
    Ideal para estimaciones rápidas de material.
    
    Args:
        elementos: Lista de categorías a sumar. Opciones: ['columnas', 'vigas', 'pisos', 'cimentacion', 'muros'].
                   Si se deja vacío, calcula todo lo estructural.
    """
    mapa = {
        "columnas": "OST_StructuralColumns",
        "cimentacion": "OST_StructuralFoundation",
        "vigas": "OST_StructuralFraming",
        "pisos": "OST_Floors",
        "muros": "OST_Walls"
    }
    
    cats_to_send = []
    
    # Si la lista está vacía o es None, asumimos todo
    if not elementos:
        cats_to_send = list(mapa.values())
    else:
        for e in elementos:
            if e.lower() in mapa:
                cats_to_send.append(mapa[e.lower()])
    
    if not cats_to_send:
        return "Error: Ninguna categoría válida seleccionada."

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "get_concrete_volume",
                "Payload": {
                    "categories": cats_to_send
                }
            }
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=60.0)
            resp.raise_for_status()
            
            data = resp.json()
            # Formateamos bonito para Claude
            texto = f"📦 **Reporte de Volumen de Concreto**\n"
            texto += f"**Total General:** {data['TotalVolumeM3']} m³\n\n"
            texto += "Desglose por categoría:\n"
            for item in data['Breakdown']:
                texto += f"- {item['Category']}: {item['Count']} elementos | {item['VolumeM3']} m³\n"
            
            return texto

    except Exception as e:
        return f"Error calculando volúmenes: {str(e)}"

@mcp.tool()
async def inventario_por_familia(categoria: str) -> str:
    """
    Genera un resumen cuantitativo agrupado por Familia y Tipo.
    Útil para conteo de puertas, ventanas, luminarias o equipos mecánicos para presupuestos.
    
    Args:
        categoria: 'puertas', 'ventanas', 'muros', 'mobiliario', 'equipos', 'fontaneria'.
    """
    mapa = {
        "puertas": "OST_Doors",
        "ventanas": "OST_Windows",
        "muros": "OST_Walls",
        "mobiliario": "OST_Furniture",
        "equipos": "OST_MechanicalEquipment",
        "fontaneria": "OST_PlumbingFixtures",
        "columnas": "OST_StructuralColumns"
    }
    
    clave = categoria.lower()
    if clave not in mapa:
        return f"Error: Categoría '{categoria}' no soportada en esta tool."
        
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "get_family_summary",
                "Payload": {
                    "category": mapa[clave]
                }
            }
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=45.0)
            resp.raise_for_status()
            
            data = resp.json()
            
            if not data:
                return f"No se encontraron elementos en la categoría {categoria}."
                
            texto = f"📊 **Inventario de {categoria.capitalize()}**\n"
            for familia in data:
                texto += f"\n🔹 **Familia: {familia['FamilyName']}**\n"
                for tipo in familia['Types']:
                    texto += f"   - Tipo: {tipo['TypeName']} | Cantidad: {tipo['Count']}\n"
            
            return texto

    except Exception as e:
        return f"Error generando inventario: {str(e)}"
####################################################################################################
## Tools de Dibujo

@mcp.tool()
async def crear_niveles(niveles: List[Dict[str, Any]]) -> str:
    """
    Crea nuevos niveles en el proyecto de Revit.
    
    Args:
        niveles: Lista de diccionarios con el 'nombre' del nivel y su 'elevacion' en metros.
                 Ejemplo: [{"nombre": "Nivel 1", "elevacion": 0.0}, {"nombre": "Nivel 2", "elevacion": 3.5}]
    """
    if not niveles:
        return "Error: No se proporcionaron niveles para crear."
        
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "create_levels", # Comando que capturaremos en C#
                "Payload": {
                    "levels": niveles
                }
            }
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=30.0)
            resp.raise_for_status()
            
            data = resp.json()
            
            # Si el servidor C# devuelve un error general
            if isinstance(data, dict) and "error" in data:
                return f"❌ Error desde Revit: {data['error']}"
                
            # Formatear la respuesta detallada para Claude
            texto = "✅ **Resultado de Creación de Niveles:**\n"
            for item in data:
                estado = item.get("Estado", "Desconocido")
                nombre = item.get("Nombre", "Sin nombre")
                if estado == "Creado":
                    texto += f"🔹 {nombre} (Elev: {item.get('ElevacionM')}m): Creado exitosamente (ID: {item.get('Id')})\n"
                else:
                    texto += f"⚠️ {nombre}: No creado - {item.get('Mensaje', 'Error desconocido')}\n"
                    
            return texto
            
    except Exception as e:
        return f"Error de conexión al crear niveles: {str(e)}"

@mcp.tool()
async def crear_ejes(ejes_verticales: List[Dict[str, Any]], ejes_horizontales: List[Dict[str, Any]]) -> str:
    """
    Crea ejes (rejillas/grids) en el proyecto. El sistema calculará automáticamente la longitud de las líneas
    para que se crucen entre sí formando una retícula perfecta.
    
    Args:
        ejes_verticales: Lista de ejes verticales (cortan el eje X). 
                         Ejemplo: [{"nombre": "1", "posicion": 0.0}, {"nombre": "2", "posicion": 5.0}]
        ejes_horizontales: Lista de ejes horizontales (cortan el eje Y). 
                           Ejemplo: [{"nombre": "A", "posicion": 0.0}, {"nombre": "B", "posicion": 4.5}]
    """
    
    # Validar que al menos haya algo que crear
    if not ejes_verticales and not ejes_horizontales:
        return "Error: Debes proporcionar al menos una lista de ejes (verticales u horizontales)."

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "Command": "create_grids",
                "Payload": {
                    "verticals": ejes_verticales if ejes_verticales else [],
                    "horizontals": ejes_horizontales if ejes_horizontales else []
                }
            }
            resp = await client.post(REVIT_BRIDGE_URL, json=payload, timeout=30.0)
            resp.raise_for_status()
            
            data = resp.json()
            
            if isinstance(data, dict) and "error" in data:
                return f"❌ Error desde Revit: {data['error']}"
            
            texto = "✅ **Resultado de Creación de Ejes:**\n"
            
            creados = [x for x in data if x.get("Estado") == "Creado"]
            errores = [x for x in data if x.get("Estado") != "Creado"]
            
            if creados:
                texto += f"✨ Se crearon {len(creados)} ejes correctamente.\n"
                # Mostrar primeros 5 como ejemplo
                ejemplos = ", ".join([f"{x['Nombre']}" for x in creados[:5]])
                texto += f"   (Ejemplos: {ejemplos}...)\n"
                
            if errores:
                texto += "\n⚠️ **Errores:**\n"
                for err in errores:
                    texto += f"- Eje {err.get('Nombre')}: {err.get('Mensaje')}\n"
            
            return texto

    except Exception as e:
        return f"Error de conexión al crear ejes: {str(e)}"

# Iniciar el servidor
if __name__ == "__main__":
    mcp.run()