# SEO de SatLink Studio

## Dominio canónico

La dirección pública definida para todas las páginas es `https://satlink-studio.vercel.app`. Las URL con `?view=...` abren una vista concreta de la consola, pero comparten la URL canónica `/` para evitar versiones duplicadas. Las páginas de contenido usan rutas limpias sin barra final; las rutas con barra final redirigen con 308.

Si el dominio público cambia, actualizar las referencias en:

- `public/index.html` (canonical, Open Graph y JSON-LD)
- `scripts/build_seo_pages.mjs` y ejecutar de nuevo `node scripts/build_seo_pages.mjs`
- `public/robots.txt`
- `public/sitemap.xml`

## Páginas indexables

- `/` — consola y presentación de SatLink
- `/radar-de-satelites` — mapa de los grupos indexados
- `/satelites-en-directo` — seguimiento de ISS, Starlink y otros objetos
- `/prediccion-de-pases` — visibilidad desde la estación
- `/enlace-satelital-doppler` — análisis de radiofrecuencia
- `/about-us` — descripción del proyecto, herramientas y procedencia de los datos

Cada página tiene título, descripción, H1, canonical, datos de Open Graph/Twitter, datos estructurados y enlaces HTML entre páginas. El contenido explica que las posiciones son cálculos basados en TLE, no telemetría directa.

## Despliegue e indexación

1. Desplegar la rama que contiene estos archivos en el proyecto de Vercel asociado a `satlink-studio.vercel.app`.
2. Confirmar que `/google0e6ee0db0637cbfb.html`, `/robots.txt`, `/sitemap.xml`, las cuatro guías y About us devuelven HTTP 200 en producción.
3. Verificar la propiedad del dominio en Google Search Console con el archivo HTML ya incluido.
4. Enviar `https://satlink-studio.vercel.app/sitemap.xml` a Search Console y solicitar inspección/indexación de las seis URL canónicas.
5. Vigilar páginas indexadas, consultas, impresiones, clics y problemas de experiencia en Search Console. Revisar también datos de Core Web Vitals de usuarios reales; priorizar el rendimiento de la consola interactiva en móvil.
6. Mantener y ampliar contenido útil según consultas reales y dudas de los usuarios. Evitar páginas casi iguales creadas solo para variantes de palabras clave.

Google decide cuándo rastrear y si indexar una URL; ni el sitemap ni la solicitud de indexación garantizan una posición concreta. La visibilidad depende también de calidad del contenido, competencia, enlaces externos y experiencia real de los visitantes.
