# Contribuir a Sistema de Horarios UABC

Gracias por contribuir.

## Principios

- Mantener cambios pequenos y enfocados.
- Evitar mezclar refactors amplios con correcciones funcionales.
- Agregar o actualizar pruebas cuando una regla de negocio cambie.
- Mantener la logica de dominio en services y la validacion de entrada en validators.

## Flujo recomendado

1. Crear una rama de trabajo descriptiva.
2. Implementar el cambio con el menor impacto posible.
3. Ejecutar pruebas relevantes antes de abrir el cambio.
4. Documentar cualquier ajuste funcional o tecnico visible.

## Convenciones practicas

- Rutas HTTP en app/api/routes.
- Reglas de negocio en app/services.
- Validaciones de payload en app/validators.
- Cambios de esquema mediante migraciones en migrations/versions.
- Documentacion tecnica en docs.

## Calidad minima esperada

- El codigo debe seguir el estilo existente del repositorio.
- No se deben introducir dependencias innecesarias.
- No se deben subir archivos generados, bases locales ni artefactos de build.

## Reporte de cambios

Al abrir un cambio, incluye:

- Problema que se corrige o mejora.
- Impacto funcional.
- Riesgos conocidos.
- Pruebas ejecutadas.