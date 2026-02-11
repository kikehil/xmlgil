import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Asistente Contable XML", layout="wide", page_icon="📊")

# Namespaces para CFDI 4.0
ns = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'pago20': 'http://www.sat.gob.mx/Pagos20'
}

def procesar_xml(archivo):
    try:
        # Leer el contenido del archivo subido
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # 1. UUID (Folio Fiscal)
        tfd = root.find('.//tfd:TimbreFiscalDigital', ns)
        uuid = tfd.attrib.get('UUID', 'N/A') if tfd is not None else "N/A"
        
        if uuid == "N/A":
            return None

        # 2. Datos Generales
        tipo_letra = root.attrib.get('TipoDeComprobante', 'I')
        nombres_tipo = {'I': 'Ingreso', 'E': 'Egreso', 'P': 'Pago', 'N': 'Nómina', 'T': 'Traslado'}
        tipo_desc = nombres_tipo.get(tipo_letra, 'Otro')

        # 3. Lógica de montos (Soporte para Pagos 2.0)
        total = float(root.attrib.get('Total', 0))
        if tipo_letra == 'P':
            pago_nodo = root.find('.//pago20:Pago', ns)
            if pago_nodo is not None:
                total = float(pago_nodo.attrib.get('Monto', 0))

        # 4. Datos de Identidad
        emisor = root.find('cfdi:Emisor', ns)
        nombre_emisor = emisor.attrib.get('Nombre', 'N/A') if emisor is not None else "N/A"

        return {
            "Fecha": root.attrib.get('Fecha', 'N/A')[:10],
            "Tipo": tipo_desc,
            "Emisor": nombre_emisor,
            "Total": total,
            "UUID": uuid,
            "Archivo": archivo.name
        }
    except Exception as e:
        return None

# --- INTERFAZ DE USUARIO ---
st.title("📊 Extractor Contable Inteligente")
st.markdown("Sube tus archivos XML para generar el reporte mensual automáticamente.")

uploaded_files = st.file_uploader("Arrastra aquí tus archivos XML", type="xml", accept_multiple_files=True)

if uploaded_files:
    datos_lista = []
    uuids_vistos = set()
    duplicados = 0

    # Procesar archivos
    for file in uploaded_files:
        resultado = procesar_xml(file)
        if resultado:
            if resultado["UUID"] in uuids_vistos:
                duplicados += 1
                continue
            uuids_vistos.add(resultado["UUID"])
            datos_lista.append(resultado)

    if datos_lista:
        df = pd.DataFrame(datos_lista)

        # Resumen métrico
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Facturas", len(df))
        col2.metric("Suma Total ($)", f"{df['Total'].sum():,.2f}")
        col3.metric("Duplicados Ignorados", duplicados)

        # Resumen por Tipo (Visualización Extra)
        st.write("### Resumen por Tipo de Comprobante")
        resumen_tipo = df.groupby('Tipo')['Total'].agg(['sum', 'count']).rename(columns={'sum': 'Total ($)', 'count': 'Cantidad'})
        st.table(resumen_tipo.style.format({'Total ($)': '{:,.2f}'}))

        # Tabla de datos
        st.subheader("Detalle de Comprobantes")
        st.dataframe(df, use_container_width=True)

        # Botón de descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte para Excel",
            data=csv,
            file_name="reporte_contable.csv",
            mime="text/csv",
        )
    else:
        st.error("No se pudo extraer información válida de los archivos subidos.")
else:
    st.info("💡 Sube tus archivos XML para visualizar el reporte.")
