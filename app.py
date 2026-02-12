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
        # Volver al inicio del archivo si ya se leyó
        archivo.seek(0)
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
        fecha = root.attrib.get('Fecha', 'N/A')[:10]
        
        tipo_letra = root.attrib.get('TipoDeComprobante', 'I')
        nombres_tipo = {'I': 'Ingreso', 'E': 'Egreso', 'P': 'Pago', 'N': 'Nómina', 'T': 'Traslado'}
        tipo_desc = nombres_tipo.get(tipo_letra, 'Otros')

        # --- Emisor y Receptor ---
        emisor = root.find('cfdi:Emisor', ns)
        receptor = root.find('cfdi:Receptor', ns)
        
        rfc_emisor = emisor.attrib.get('Rfc', 'N/A') if emisor is not None else "N/A"
        nom_emisor = emisor.attrib.get('Nombre', 'N/A') if emisor is not None else "N/A"
        
        rfc_receptor = receptor.attrib.get('Rfc', 'N/A') if receptor is not None else "N/A"
        nom_receptor = receptor.attrib.get('Nombre', 'N/A') if receptor is not None else "N/A"
        uso_cfdi = receptor.attrib.get('UsoCFDI', 'N/A') if receptor is not None else "N/A"

        # --- Importes ---
        total = float(root.attrib.get('Total', 0))

        # Caso especial para Pagos (Complemento de Recepción de Pagos)
        if tipo_letra == 'P':
            pago_nodo = root.find('.//pago20:Pago', ns)
            if pago_nodo is not None:
                total = float(pago_nodo.attrib.get('Monto', 0))

        # --- Lógica de Alerta Fiscal ---
        alerta_fiscal = "✅ Deducible"
        if tipo_desc == 'Ingreso':
            if forma_pago == '01' and total > 2000:
                alerta_fiscal = "❌ Efectivo > $2k"
            elif uso_cfdi in ['S01', 'CP01']:
                alerta_fiscal = "❌ Sin Efectos Fiscales"
        elif tipo_desc in ['Pago', 'Nómina']:
            alerta_fiscal = "✅ Informativo"

        return {
            "Fecha": fecha,
            "Tipo": tipo_desc,
            "Rfc Emisor": rfc_emisor,
            "Nombre Emisor": nom_emisor,
            "Rfc Receptor": rfc_receptor,
            "Nombre Receptor": nom_receptor,
            "UsoCFDI": uso_cfdi,
            "MetodoPago": metodo_pago,
            "FormaPago": forma_pago,
            "Total": total,
            "Alerta Fiscal": alerta_fiscal,
            "UUID": uuid,
            "Folio": f"{serie}{folio}"
        }
    except Exception as e:
        return None

# Función para generar el Excel con 5 pestañas
def generar_excel_contable(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Hoja BASE (Todos los registros)
        df.to_excel(writer, sheet_name='BASE', index=False)
        
        # 2. Hoja NOMINA (Tipo Nómina)
        df[df['Tipo'] == 'Nómina'].to_excel(writer, sheet_name='NOMINA', index=False)
        
        # 3. Hoja COMPLEMENTO DE PAGO (Tipo Pago)
        df[df['Tipo'] == 'Pago'].to_excel(writer, sheet_name='COMPLEMENTO_PAGO', index=False)
        
        # 4. Hoja DEDUCIBLES
        # Filtro: No es nómina, no es pago, y cumple regla de efectivo o uso deducible
        deducibles = df[
            (df['Tipo'] == 'Ingreso') & 
            (df['Alerta Fiscal'].str.contains('✅'))
        ]
        deducibles.to_excel(writer, sheet_name='DEDUCIBLES', index=False)
        
        # 5. Hoja NO DEDUCIBLES
        no_deducibles = df[df['Alerta Fiscal'].str.contains('❌')]
        no_deducibles.to_excel(writer, sheet_name='NO_DEDUCIBLES', index=False)
        
    return output.getvalue()

# --- INTERFAZ STREAMLIT ---
st.title("📂 Sistema Contable Multi-Hoja")
st.markdown("Sube tus archivos XML para generar el reporte contable avanzado.")

uploaded_files = st.file_uploader("Arrastra aquí tus archivos XML", type="xml", accept_multiple_files=True)

if uploaded_files:
    datos_lista = []
    uuids_vistos = set()
    duplicados = 0

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

        # --- TARJETAS DE TOTALES ---
        st.subheader("📊 Resumen por Concepto")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1: st.metric("General", f"${df['Total'].sum():,.2f}")
        with c2: 
            total_nom = df[df['Tipo'] == 'Nómina']['Total'].sum()
            st.metric("Nómina", f"${total_nom:,.2f}")
        with c3:
            total_pago = df[df['Tipo'] == 'Pago']['Total'].sum()
            st.metric("Pagos", f"${total_pago:,.2f}")
        with c4:
            total_ded = df[(df['Tipo'] == 'Ingreso') & (df['Alerta Fiscal'].str.contains('✅'))]['Total'].sum()
            st.metric("Deducible", f"${total_ded:,.2f}")
        with c5:
            total_noded = df[df['Alerta Fiscal'].str.contains('❌')]['Total'].sum()
            st.metric("No Deducible", f"${total_noded:,.2f}", delta_color="inverse")

        # --- TABLA DE DATOS ---
        st.subheader("📋 Vista Previa de Documentos")
        st.dataframe(df, use_container_width=True)

        # --- BOTÓN DE DESCARGA ---
        st.divider()
        excel_data = generar_excel_contable(df)
        st.download_button(
            label="📥 Descargar Libro Contable (5 Hojas)",
            data=excel_data,
            file_name="Auditoria_Contable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        if duplicados > 0:
            st.warning(f"Se omitieron {duplicados} archivos duplicados.")
    else:
        st.error("No se pudo extraer información válida de los archivos subidos.")
else:
    st.info("💡 Sube tus archivos XML para comenzar el análisis contable.")
