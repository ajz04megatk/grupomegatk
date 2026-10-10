# Próximos conectores y reserva en línea

La cita clínica vive en `odental.appointment`. El profesional decide la hora
desde su agenda personal cuando la conexión está activa; recepción también
puede editarla en O Dental. Si ambos lados cambian la hora antes de conciliar,
se aplica la del profesional. Una colisión con otra cita queda marcada para
revisión y nunca desplaza a un segundo paciente de forma silenciosa.

## Agendas personales adicionales

El único conector implementado actualmente es **Todoist**. Preparar una
configuración común por profesional y organización para seleccionar fuentes de
disponibilidad y un destino de citas por proveedor. Mantener cada conexión
independiente: credencial del titular, calendario/proyecto de destino,
activación, última sincronización y errores. No mostrar proveedores como
«conectados» hasta completar su adaptador y una prueba de ida y vuelta.

Priorizar **Google Calendar**, **Microsoft Outlook/Microsoft 365** y
**Apple Calendar/iCloud**; evaluar después otros calendarios solicitados por
profesionales. Cada adaptador necesita identificador externo, fechas UTC,
organización, profesional, última versión conciliada y política de cancelación.
Importar solo intervalos ocupados privados; los eventos clínicos salientes
mostrarán únicamente los datos mínimos que autorice la clínica. Identificar y
excluir eventos generados por O Dental para evitar bucles y bloqueos duplicados
cuando una persona ya sincronice Todoist, Google u Outlook entre sí. Si dos
agendas intentan modificar la misma cita, conservar un histórico y pedir
revisión ante cambios incompatibles; no cancelar ni desplazar pacientes de
forma silenciosa. Verificar autenticación, permisos y capacidades de cada
proveedor antes de conectarlo. No activar cuentas sin autorización del titular.

## Enlace para pacientes

Implementar por organización, sede, profesional y servicio. El enlace para
invitación debe tener token revocable y vencimiento; la clínica también podrá
habilitar una página pública separadamente. Mostrar solo horas disponibles,
nunca nombres de pacientes ni contenido de agendas personales.

Calcular huecos con horarios de atención, descansos, duración del servicio,
preparación/limpieza, consultorio y equipos; descontar citas clínicas, bloqueos
personales y solicitudes pendientes. Pedir únicamente datos de contacto y
consentimiento, validar de nuevo el hueco al enviar y evitar reservas
simultáneas. La primera versión crea una **solicitud pendiente** para recepción;
confirmarla genera la cita clínica y sincroniza la agenda del profesional.
La confirmación automática puede habilitarse después de probar recursos,
colisiones y aislamiento por empresa. Nunca exponer expedientes al público.

Odoo 18 tiene su propia aplicación Citas con enlaces compartibles, pero una
reserva allí no debe considerarse cita O Dental hasta construir y probar un
puente con `odental.appointment` y sus reglas de disponibilidad.
