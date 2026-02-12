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

# Iniciar el servidor
if __name__ == "__main__":
    mcp.run()