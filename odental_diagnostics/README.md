# O Dental Odontograma e Imágenes

Tercer bloque funcional de O Dental para Odoo 18.

Incluye catálogo FDI de 52 piezas permanentes y temporales, hallazgos por superficie,
odontogramas firmados con rectificaciones versionadas, archivos clínicos en el filestore
de Odoo, metadatos DICOM, huella SHA-256, privacidad selectiva y auditoría.

## Gráfico dental

En el formulario del odontograma se muestran las arcadas permanente, temporal o ambas
para la dentición mixta. Las piezas siguen la numeración FDI. Las zonas coloreadas
resumen hallazgos existentes, planificados, realizados y en observación; la lista de
hallazgos bajo el gráfico conserva los detalles y las notas clínicas.

Guarde primero un odontograma en borrador. Después seleccione una pieza o superficie
del gráfico para registrar un hallazgo mediante el formulario clínico. Si ya existe
un solo hallazgo en esa zona, el formulario lo abre para su revisión. Una zona con
varios hallazgos se consulta en la lista inferior. La firma bloquea modificaciones;
las correcciones se hacen mediante una rectificación versionada.

El dibujo es un esquema clínico, no una radiografía ni un diagnóstico automático.
Las imágenes clínicas y DICOM se gestionan en el repositorio de imágenes del expediente.

## Próximo cambio: selector de piezas con número y descripción

La ventana «Buscar: Pieza» muestra actualmente solo el nombre del diente en una
columna «Name». En el próximo cambio, tanto el selector corto como «Buscar más»
mostrarán el número y la descripción juntos según el sistema elegido en el
odontograma: por ejemplo, «18 · Tercer molar superior derecho» en FDI y
«1 · Tercer molar superior derecho» en ADA. La lista llevará la columna «Pieza».

La búsqueda debe aceptar número FDI, número ADA y nombre, también para dientes
temporales. El contexto FDI/ADA debe llegar al selector en línea y al formulario
de hallazgos. Se conservará el identificador de la pieza y sus datos clínicos;
el gráfico compacto puede seguir mostrando solo el número.

Criterios de comprobación en staging: la misma pieza aparece con ambos códigos
y descripción al cambiar la notación; «Buscar más» muestra la numeración; buscar
por código o nombre encuentra la pieza; seleccionar un diente temporal funciona;
los hallazgos existentes mantienen su referencia. Archivos previstos:
`models/tooth.py`, `views/odontogram_views.xml` y pruebas dirigidas.
