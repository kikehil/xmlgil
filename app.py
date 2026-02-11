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
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # --- Datos de Identificación (Complemento Fiscal) ---
        tfd = root.find('.//tfd:TimbreFiscalDigital', ns)
        uuid = tfd.attrib.get('UUID', 'N/A') if tfd is not None else "N/A"
        
        # --- Datos de la Factura (Atributos de Raíz) ---
        folio = root.attrib.get('Folio', 'S/F')
        serie = root.attrib.get('Serie', '')
        metodo_pago = root.attrib.get('MetodoPago', 'N/A')
        forma_pago = root.attrib.get('FormaPago', 'N/A')
        no_certificado = root.attrib.get('NoCertificado', 'N/A')
        fecha = root.attrib.get('Fecha', 'N/A')[:10]

        # --- Emisor y Receptor ---
        emisor = root.find('cfdi:Emisor', ns)
        receptor = root.find('cfdi:Receptor', ns)
        
        rfc_emisor = emisor.attrib.get('Rfc', 'N/A') if emisor is not None else "N/A"
        nom_emisor = emisor.attrib.get('Nombre', 'N/A') if emisor is not None else "N/A"
        
        rfc_receptor = receptor.attrib.get('Rfc', 'N/A') if receptor is not None else "N/A"
        nom_receptor = receptor.attrib.get('Nombre', 'N/A') if receptor is not None else "N/A"
        uso_cfdi = receptor.attrib.get('UsoCFDI', 'N/A') if receptor is not None else "N/A"

        # --- Importes y Totales ---
        subtotal = float(root.attrib.get('SubTotal', 0))
        total = float(root.attrib.get('Total', 0))

        # --- Impuestos (Traslados y Retenciones) ---
        iva_trasladado = 0.0
        impuestos_retenidos = 0.0
        
        impuestos_global = root.find('cfdi:Impuestos', ns)
        if impuestos_global is not None:
            # Sumar todos los traslados (IVA, IEPS)
            traslados = impuestos_global.find('cfdi:Traslados', ns)
            if traslados is not None:
                for t in traslados.findall('cfdi:Traslado', ns):
                    iva_trasladado += float(t.attrib.get('Importe', 0))
            
            # Sumar todas las retenciones (ISR, IVA Retenido)
            retenciones = impuestos_global.find('cfdi:Retenciones', ns)
            if retenciones is not None:
                for r in retenciones.findall('cfdi:Retencion', ns):
                    impuestos_retenidos += float(r.attrib.get('Importe', 0))

        return {
            "Rfc Emisor": rfc_emisor,
            "Nombre Emisor": nom_emisor,
            "Rfc Receptor": rfc_receptor,
            "Nombre Receptor": nom_receptor,
            "UsoCFDI": uso_cfdi,
            "Folio": f"{serie}{folio}",
            "NoCertificado": no_certificado,
            "MetodoPago": metodo_pago,
            "FormaPago": forma_pago,
            "SUBTOTAL": subtotal,
            "IMPUESTOS TRASLADADOS": iva_trasladado,
            "IMPUESTOS RETENIDOS": impuestos_retenidos,
            "TOTAL": total,
            "Fecha": fecha,
            "UUID": uuid
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
        col2.metric("Suma Total ($)", f"{df['TOTAL'].sum():,.2f}")
        col3.metric("Duplicados Ignorados", duplicados)

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
