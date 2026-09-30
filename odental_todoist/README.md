# Disponibilidad de O Dental desde Todoist

Piloto para bloquear horas en la Agenda O Dental a partir de tareas de Todoist
del profesional. El personal de la clínica solo ve **No disponible**, el
profesional y el intervalo; títulos, descripciones y proyectos no se copian.

## Preparación

1. Actualizar `odental_core` e instalar `odental_todoist` en una base de prueba.
2. Verificar que el usuario de Odoo del odontólogo tenga el grupo **Profesional**,
   esté enlazado a su ficha de profesional y que esa ficha pertenezca a la
   organización y compañía clínicas correctas. Esto es necesario para que
   aparezca **O Dental → Clínica → Conectar mi Todoist**. No añadir otras
   compañías ni permisos de administración generales.
3. El profesional obtiene su token personal en su propia cuenta de Todoist y
   lo pega directamente en el formulario de Odoo. No enviarlo por chat ni a la
   recepcionista. Elegir etiqueta `reunión` y zona `America/Tegucigalpa`.
4. Crear en Todoist una tarea con la etiqueta `@reunión` y fecha **con hora**.
   Si Todoist permite duración explícita, se respeta; en una cuenta sin esa
   función se usa la duración predeterminada (60 minutos, configurable).
   Se importa como bloqueo privado al conectar y luego
   aproximadamente cada dos minutos. También se puede pulsar **Actualizar ahora**.

Al completar, eliminar o quitar la etiqueta, el siguiente sondeo cancela el
bloqueo en O Dental y libera el horario. Al cambiar hora o duración, mueve el
mismo bloqueo. Una cita clínica preexistente no se borra si entra un bloqueo
externo con conflicto: el formulario del bloqueo señala la coincidencia para
revisión humana. No se escriben ni modifican tareas en Todoist.

Las tareas sin hora no bloquean. Las fallas de API o
respuestas incompletas mantienen los bloqueos anteriores y dejan un estado de
error en **Mi disponibilidad Todoist**; el horario requiere revisión hasta que
se restablezca la sincronización. **Desconectar** borra el token almacenado y
libera los bloqueos de esa conexión, con confirmación visible.

## Prueba de aceptación

- Crear tarea de prueba 10:00–11:00 con etiqueta `@reunión`; actualizar y
  comprobar **No disponible** en Agenda y rechazo de una nueva cita solapada.
- Moverla a 12:00; actualizar y comprobar disponible 10:00–11:00 y ocupado
  12:00–13:00.
- Completarla; actualizar y comprobar liberado 12:00–13:00, con el bloqueo
  cancelado fuera de la Agenda habitual.
- Repetir desde un usuario de otra clínica: no debe ver ni administrar la
  conexión, la tarea o la cita clínica de la primera organización.

Este módulo no integra Google Calendar, Outlook, Apple Calendar ni relojes;
esas fuentes requieren sus propios conectores y una política contra bloqueos
duplicados antes de activarse conjuntamente.
