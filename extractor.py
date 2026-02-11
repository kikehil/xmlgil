import xml.etree.ElementTree as ET
import csv
import os
import shutil
from collections import defaultdict

# Configuración
carpeta_entrada = "facturas_xml"
carpeta_organizada = "Facturas_Organizadas"
archivo_salida = "sistema_contable_pro.csv"

ns = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'pago20': 'http://www.sat.gob.mx/Pagos20'
}

def extraer_y_organizar(ruta_archivo):
    try:
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()

        # 1. UUID y Fecha para organizar
        tfd = root.find('.//tfd:TimbreFiscalDigital', ns)
        uuid = tfd.attrib.get('UUID', 'N/A') if tfd is not None else "N/A"
        fecha_full = root.attrib.get('Fecha', '0000-00-00')
        anio = fecha_full[0:4]
        mes = fecha_full[5:7]

        if uuid == "N/A": return None, None

        # 2. Datos Contables
        tipo_letra = root.attrib.get('TipoDeComprobante', 'I')
        nombres_tipo = {'I': 'Ingreso', 'E': 'Egreso', 'P': 'Pago', 'N': 'Nomina', 'T': 'Traslado'}
        tipo_desc = nombres_tipo.get(tipo_letra, 'Otros')

        total = float(root.attrib.get('Total', 0))
        if tipo_letra == 'P':
            pago_nodo = root.find('.//pago20:Pago', ns)
            if pago_nodo is not None:
                total = float(pago_nodo.attrib.get('Monto', 0))

        # 3. Crear carpeta de destino y organizar
        # Ruta: Facturas_Organizadas / 2026 / 01 / Ingreso
        ruta_destino = os.path.join(carpeta_organizada, anio, mes, tipo_desc)
        if not os.path.exists(ruta_destino):
            os.makedirs(ruta_destino)
        
        shutil.copy(ruta_archivo, os.path.join(ruta_destino, os.path.basename(ruta_archivo)))

        datos = {
            "Fecha": fecha_full[:10],
            "Tipo": tipo_desc,
            "Nombre Emisor": root.find('cfdi:Emisor', ns).attrib.get('Nombre', 'N/A'),
            "Total Real": total,
            "UUID": uuid,
            "Ubicacion": f"{anio}/{mes}/{tipo_desc}"
        }
        return datos, uuid
    except Exception:
        return None, None

def iniciar_proceso():
    if not os.path.exists(carpeta_entrada):
        os.makedirs(carpeta_entrada)
        print(f"Por favor, coloca tus XML en la carpeta '{carpeta_entrada}'.")
        return

    reporte = []
    uuids_vistos = set()
    resumen = defaultdict(float)
    duplicados = 0

    for f in os.listdir(carpeta_entrada):
        if f.endswith(".xml"):
            res, uuid = extraer_y_organizar(os.path.join(carpeta_entrada, f))
            if uuid:
                if uuid in uuids_vistos:
                    duplicados += 1
                    continue
                uuids_vistos.add(uuid)
                reporte.append(res)
                resumen[res["Tipo"]] += res["Total Real"]

    if reporte:
        # Guardar reporte detallado
        with open(archivo_salida, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=reporte[0].keys())
            writer.writeheader()
            writer.writerows(reporte)

        print("\n" + " PROCESO COMPLETADO ".center(40, "="))
        for t, s in resumen.items():
            print(f"{t:15} | $ {s:15,.2f}")
        print("-" * 40)
        print(f"Archivos organizados en: {carpeta_organizada}")
        print(f"Duplicados evitados:     {duplicados}")
        print("=" * 40)

if __name__ == "__main__":
    iniciar_proceso()
