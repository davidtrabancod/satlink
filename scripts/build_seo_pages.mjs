// Generates lightweight, crawlable pages for the main SatLink search intents.
// Run with: node scripts/build_seo_pages.mjs
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const origin = 'https://satlink-studio.vercel.app';
const pages = [
  {
    slug: 'radar-de-satelites',
    title: 'Radar de satélites en directo | SatLink Studio',
    description: 'Explora un mapa de satélites con posiciones estimadas de la ISS, Starlink y otros grupos. Filtra objetos, consulta sus órbitas y abre su ficha NORAD.',
    eyebrow: '01 / SAT-RADAR',
    heading: 'Radar de satélites',
    lead: 'Explora los satélites del catálogo en un mapa, filtra constelaciones y abre la ficha orbital de cada objeto.',
    view: 'radar',
    cta: 'Abrir el radar de satélites',
    body: `
      <section><h2>Mapa de satélites en directo y fichas orbitales</h2><p>Sat-Radar representa la posición estimada de los objetos incluidos en los catálogos de estaciones, Starlink, órbita geoestacionaria y satélites activos. Cada punto del mapa puede seleccionarse para consultar su nombre, identificador NORAD, latitud, longitud, altitud, velocidad, inclinación y periodo orbital. Puedes activar o desactivar grupos, buscar por nombre o NORAD y acercarte a una región concreta.</p><p>El mapa actualiza las posiciones calculadas aproximadamente cada 10 segundos mientras está abierto. La vista de relieve aparece al acercarte; los controles permiten ampliar el zoom y desplazar el mapa.</p></section>
      <section><h2>¿Qué significa «en directo»?</h2><p>Las posiciones se calculan con el modelo orbital SGP4 a partir de elementos TLE publicados por CelesTrak. No son señales GPS recibidas directamente de los satélites. La frecuencia de dibujo no equivale a la frecuencia de actualización de los datos orbitales: un TLE antiguo o una maniobra reciente pueden hacer que la posición estimada difiera de la real. Si un grupo no está disponible, el radar puede mostrar solo los grupos accesibles.</p></section>
      <section><h2>Cómo usar Sat-Radar</h2><ol><li>Abre el radar y selecciona las capas que quieras ver.</li><li>Usa la búsqueda para localizar una misión o un número NORAD.</li><li>Selecciona un círculo del mapa para abrir su ficha orbital.</li><li>Acerca el mapa para explorar el relieve y la zona bajo la trayectoria.</li></ol><p>Si prefieres seguir un único objeto, consulta la guía de <a href="/satelites-en-directo">seguimiento de satélites en directo</a>. Para saber cuándo pasará sobre ti, utiliza la <a href="/prediccion-de-pases">predicción de pases</a>.</p></section>`
  },
  {
    slug: 'satelites-en-directo',
    title: 'Satélites en directo: ISS y Starlink | SatLink Studio',
    description: 'Sigue satélites en directo sobre el globo 3D y el mapa 2D. Consulta la posición calculada de la ISS, Starlink y otros objetos y entiende cómo se obtiene.',
    eyebrow: '02 / SEGUIMIENTO',
    heading: 'Satélites en directo',
    lead: 'Selecciona un satélite y observa su trayectoria terrestre, su posición orbital y las magnitudes clave de su movimiento.',
    view: 'globe',
    cta: 'Abrir el seguimiento orbital',
    body: `
      <section><h2>¿Dónde está la ISS ahora? Sigue también Starlink</h2><p>SatLink Studio permite elegir un objeto de los grupos de estaciones, Starlink, geoestacionarios y satélites activos. Puedes buscar por nombre o número NORAD y consultar su latitud, longitud, altitud y velocidad. La vista de globo 3D ayuda a entender la órbita alrededor de la Tierra; el tracker 2D muestra la trayectoria sobre el mapa terrestre.</p><p>El satélite seleccionado también sirve de referencia para las otras herramientas de la consola: la predicción de pases y el análisis de enlace. Así puedes pasar de una posición global a una pregunta concreta: ¿cuándo estará por encima de mi estación?</p></section>
      <section><h2>Cómo se calcula la posición</h2><p>El seguimiento utiliza elementos orbitales TLE y propagación orbital. En cada actualización, SatLink estima dónde debería encontrarse el satélite en ese instante. «En directo» describe el cálculo y la visualización continuos, no una conexión de telemetría con el vehículo. La calidad depende de la vigencia del TLE, del tipo de órbita y de posibles maniobras que aún no estén reflejadas en los datos.</p></section>
      <section><h2>Empieza con una misión</h2><ol><li>Abre la consola orbital y elige un grupo en el panel lateral.</li><li>Busca ISS, un satélite Starlink u otro objeto del catálogo.</li><li>Alterna entre globo 3D y tracker 2D en «Vista activa».</li><li>Introduce tu ubicación para calcular la visibilidad local.</li></ol><p>Si quieres inspeccionar muchos objetos a la vez, abre el <a href="/radar-de-satelites">radar de satélites</a>. Para planificar una observación, revisa los <a href="/prediccion-de-pases">próximos pases</a>.</p></section>`
  },
  {
    slug: 'prediccion-de-pases',
    title: 'Predicción de pases de satélites | SatLink Studio',
    description: 'Calcula los próximos pases de un satélite sobre tu ubicación: AOS, máxima elevación y LOS. Ajusta la estación y la máscara de elevación en SatLink Studio.',
    eyebrow: '03 / VISIBILIDAD',
    heading: 'Predicción de pases',
    lead: 'Descubre cuándo aparecerá un satélite sobre el horizonte de tu estación y cuánto tiempo permanecerá visible geométricamente.',
    view: 'passes',
    cta: 'Calcular los próximos pases',
    body: `
      <section><h2>Planea una observación satelital</h2><p>La predicción de pases cruza la órbita estimada del satélite con las coordenadas de tu estación terrestre. SatLink calcula ventanas para los próximos tres días y muestra momentos relevantes como AOS (adquisición de señal), máxima elevación y LOS (pérdida de señal). Puedes introducir latitud, longitud y altitud manualmente o usar la ubicación del navegador si concedes permiso.</p></section>
      <section><h2>Qué es la máscara de elevación</h2><p>La máscara define la altura mínima sobre el horizonte que debe alcanzar el satélite para que el pase se considere útil. Una máscara más alta puede excluir pasos bajos, que suelen estar más afectados por obstáculos y mayor distancia oblicua. Cambia este valor según la geometría de tu estación y las condiciones locales.</p><p>La predicción indica visibilidad geométrica, no garantiza que puedas ver el satélite a simple vista. La iluminación solar, el clima, los edificios, la sensibilidad del receptor y la vigencia del TLE también importan.</p></section>
      <section><h2>Cómo calcular un pase</h2><ol><li>Selecciona un satélite en la consola.</li><li>Define la ubicación de la estación o pulsa «Usar mi ubicación».</li><li>Ajusta la máscara de elevación.</li><li>Abre «Predicción de pases» en el selector de vistas.</li></ol><p>Consulta antes el <a href="/satelites-en-directo">seguimiento orbital</a> si aún no has elegido objeto. Si tu objetivo es un enlace de radio, completa la planificación con el <a href="/enlace-satelital-doppler">cálculo de enlace y Doppler</a>.</p></section>`
  },
  {
    slug: 'enlace-satelital-doppler',
    title: 'Enlace satelital y efecto Doppler | SatLink Studio',
    description: 'Simula un enlace satelital con distancia oblicua, pérdida en espacio libre, potencia recibida, C/N, Eb/N₀, margen y desplazamiento Doppler.',
    eyebrow: '04 / RADIOFRECUENCIA',
    heading: 'Enlace satelital y Doppler',
    lead: 'Estima cómo la geometría orbital y los parámetros de radio afectan a un enlace entre un satélite y tu estación.',
    view: 'rf',
    cta: 'Abrir el simulador de enlace',
    body: `
      <section><h2>Del satélite a la señal recibida</h2><p>SatLink calcula la distancia oblicua entre el objeto seleccionado y la estación terrestre, la pérdida de propagación en espacio libre, la potencia recibida, la relación portadora/ruido, Eb/N₀ y el margen de enlace. También estima el desplazamiento Doppler a partir de la velocidad radial, para la frecuencia que indiques.</p></section>
      <section><h2>Parámetros que debes conocer</h2><p>Introduce la frecuencia, la potencia del transmisor, las ganancias y pérdidas de las antenas, el ancho de banda y la temperatura de ruido del sistema. Estos parámetros son supuestos editables: no proceden del TLE ni describen necesariamente el equipo real de un satélite. Un margen positivo en este modelo tampoco garantiza por sí solo una comunicación fiable; pueden intervenir interferencias, polarización, atmósfera, apuntamiento y obstáculos.</p></section>
      <section><h2>Cómo interpretar el Doppler</h2><p>Cuando la distancia entre satélite y estación cambia, la frecuencia observada se desplaza. El signo y la magnitud de la estimación dependen de si el satélite se aproxima o se aleja y de la frecuencia de operación. El valor mostrado es una ayuda para analizar el escenario, no una corrección automática aplicada a una radio.</p><p>Para elegir una buena ventana temporal, consulta primero la <a href="/prediccion-de-pases">predicción de pases</a>. Puedes revisar la órbita en el <a href="/satelites-en-directo">seguimiento en directo</a>.</p></section>`
  }
];

const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const toolNames = { radar: 'Sat-Radar', globe: 'Globo 3D', passes: 'Predicción de pases', rf: 'Enlace y Doppler' };
const cardNav = (view) => `<nav class="sat-card-nav" data-open="false" aria-label="Navegación principal"><div class="card-nav-bar" data-nosnippet><button class="card-nav-toggle" type="button" aria-expanded="false" aria-controls="sat-main-menu"><span class="card-nav-lines" aria-hidden="true"><i></i><i></i></span><span class="card-nav-toggle-label">Menú</span></button><a class="card-nav-brand" href="/" aria-label="SatLink Studio, consola"><span class="card-nav-brand-icon" aria-hidden="true">◎</span><span>SATLINK<small>ORBITAL STUDIO</small></span></a><a class="card-nav-quick" data-console-return href="/?view=${view}">Volver a la consola <span aria-hidden="true">↗</span></a></div><div class="card-nav-panel" id="sat-main-menu" data-nosnippet><a class="card-nav-card" data-console-return href="/?view=${view}"><span class="card-nav-index">01 / EXPLORAR <span aria-hidden="true">◎</span></span><strong>Consola</strong><span class="card-nav-description">Radar, globo y herramientas orbitales en una sola vista.</span><span class="card-nav-action">Abrir consola <span aria-hidden="true">↗</span></span></a><a class="card-nav-card is-current" href="/#guias" aria-current="location"><span class="card-nav-index">02 / APRENDER <span aria-hidden="true">✦</span></span><strong>Guías</strong><span class="card-nav-description">Entiende los datos y descubre qué puedes calcular.</span><span class="card-nav-action">Explorar guías <span aria-hidden="true">↗</span></span></a><a class="card-nav-card" href="/about-us"><span class="card-nav-index">03 / PROYECTO <span aria-hidden="true">⌁</span></span><strong>About us</strong><span class="card-nav-description">Conoce SatLink y cómo interpreta las órbitas.</span><span class="card-nav-action">Conocer el proyecto <span aria-hidden="true">↗</span></span></a></div></nav>`;

await mkdir(join('public', 'seo'), { recursive: true });
for (const page of pages) {
  const url = `${origin}/${page.slug}`;
  const nav = pages.map((other) => `<a href="/${other.slug}"${other.slug === page.slug ? ' aria-current="page"' : ''}>${escape(other.heading)}</a>`).join('');
  const schema = JSON.stringify({
    '@context': 'https://schema.org',
    '@graph': [
      { '@type': 'WebPage', name: page.title, url, description: page.description, inLanguage: 'es', isPartOf: { '@type': 'WebSite', name: 'SatLink Studio', url: `${origin}/` } },
      { '@type': 'BreadcrumbList', itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'SatLink Studio', item: `${origin}/` },
        { '@type': 'ListItem', position: 2, name: page.heading, item: url }
      ] }
    ]
  });
  const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#070812">
  <title>${escape(page.title)}</title>
  <meta name="description" content="${escape(page.description)}">
  <link rel="canonical" href="${url}">
  <link rel="icon" type="image/png" sizes="64x64" href="/favicon.png">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="es_ES">
  <meta property="og:site_name" content="SatLink Studio">
  <meta property="og:title" content="${escape(page.title)}">
  <meta property="og:description" content="${escape(page.description)}">
  <meta property="og:url" content="${url}">
  <meta property="og:image" content="${origin}/og-satlink.png">
  <meta property="og:image:alt" content="SatLink Studio: radar de satélites en directo y control orbital.">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escape(page.title)}">
  <meta name="twitter:description" content="${escape(page.description)}">
  <meta name="twitter:image" content="${origin}/og-satlink.png">
  <script type="application/ld+json">${schema}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/seo-pages.css?v=4">
  <link rel="stylesheet" href="/card-nav.css?v=9">
  <script src="/seo-navigation.js?v=1" defer></script>
  <script src="/card-nav.js?v=5" defer></script>
</head>
<body>
  <div class="atmosphere" aria-hidden="true"></div>
  <header class="site-header">${cardNav(page.view)}<nav class="guide-nav" aria-label="Guías de SatLink"><span>GUÍAS</span>${nav}</nav></header>
  <main id="main">
    <nav class="breadcrumbs" aria-label="Ruta de navegación"><a data-console-return href="/?view=${page.view}">Consola</a><span aria-hidden="true">/</span><span>Guías</span><span aria-hidden="true">/</span><span aria-current="page">${escape(page.heading)}</span></nav>
    <div class="hero"><div class="orbit-art" aria-hidden="true"><i></i><i></i><i></i><span></span></div><div class="hero-copy"><div class="eyebrow"><span></span>GUÍA · ${escape(page.eyebrow)}</div><h1>${escape(page.heading)}<em>.</em></h1><p>${escape(page.lead)}</p><a class="primary-cta" href="/?view=${page.view}">Abrir ${escape(toolNames[page.view])} <span aria-hidden="true">↗</span></a></div></div>
    <div class="content-layout"><article class="article">${page.body}</article><aside class="aside"><div class="aside-kicker">HERRAMIENTA RELACIONADA</div><h2>${escape(toolNames[page.view])}</h2><p>Esta guía explica lo que verás en la consola. Cuando quieras probarlo, abre la herramienta.</p><a class="aside-console" href="/?view=${page.view}">Usar la herramienta <span aria-hidden="true">↗</span></a><a data-console-return href="/?view=${page.view}">Volver a mi vista <span aria-hidden="true">←</span></a></aside></div>
    <div class="method-note"><strong>Sobre los datos</strong><p>SatLink calcula posiciones mediante propagación orbital a partir de elementos TLE. Las estimaciones no sustituyen datos de telemetría ni información operacional para decisiones críticas. Fuente de elementos orbitales: <a href="https://celestrak.org/" target="_blank" rel="noopener noreferrer">CelesTrak</a>.</p></div>
  </main>
  <footer class="site-footer"><span>© SATLINK STUDIO</span><a data-console-return href="/?view=${page.view}">Volver a la consola ↗</a></footer>
</body>
</html>
`;
  await writeFile(join('public', 'seo', `${page.slug}.html`), html, 'utf8');
}
const aboutTitle = 'Sobre SatLink Studio | Radar y seguimiento satelital';
const aboutDescription = 'Conoce SatLink Studio, una herramienta para explorar el radar de satélites, seguir la ISS y Starlink, calcular pases y analizar órbitas estimadas.';
const aboutUrl = `${origin}/about-us`;
const aboutSchema = JSON.stringify({ '@context': 'https://schema.org', '@graph': [
  { '@type': 'AboutPage', name: aboutTitle, url: aboutUrl, description: aboutDescription, inLanguage: 'es', isPartOf: { '@type': 'WebSite', name: 'SatLink Studio', url: `${origin}/` } },
  { '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'SatLink Studio', item: `${origin}/` }, { '@type': 'ListItem', position: 2, name: 'About us', item: aboutUrl }] }
] });
const aboutHtml = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#070812">
  <title>${aboutTitle}</title>
  <meta name="description" content="${aboutDescription}">
  <link rel="canonical" href="${aboutUrl}">
  <link rel="icon" type="image/png" sizes="64x64" href="/favicon.png">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="es_ES">
  <meta property="og:site_name" content="SatLink Studio">
  <meta property="og:title" content="${aboutTitle}">
  <meta property="og:description" content="${aboutDescription}">
  <meta property="og:url" content="${aboutUrl}">
  <meta property="og:image" content="${origin}/og-satlink.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${aboutTitle}">
  <meta name="twitter:description" content="${aboutDescription}">
  <meta name="twitter:image" content="${origin}/og-satlink.png">
  <script type="application/ld+json">${aboutSchema}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/seo-pages.css?v=5">
  <link rel="stylesheet" href="/card-nav.css?v=9">
  <link rel="stylesheet" href="/about.css?v=1">
  <script src="/seo-navigation.js?v=1" defer></script>
  <script src="/card-nav.js?v=5" defer></script>
</head>
<body>
  <div class="atmosphere" aria-hidden="true"></div>
  <header class="site-header">${cardNav('globe').replace('class="card-nav-card is-current" href="/#guias" aria-current="location"', 'class="card-nav-card" href="/#guias"').replace('class="card-nav-card" href="/about-us"', 'class="card-nav-card is-current" href="/about-us" aria-current="page"')}</header>
  <main id="main">
    <nav class="breadcrumbs" aria-label="Ruta de navegación"><a data-console-return href="/?view=globe">Consola</a><span aria-hidden="true">/</span><span aria-current="page">About us</span></nav>
    <div class="hero about-hero"><div class="orbit-art" aria-hidden="true"><i></i><i></i><i></i><span></span></div><div class="hero-copy"><div class="eyebrow"><span></span>EL PROYECTO / SATLINK STUDIO</div><h1>Sobre SatLink<br><em>Studio.</em></h1><p>Una herramienta para explorar el radar de satélites, seguir la ISS y Starlink y entender los cálculos orbitales de cada vista.</p><a class="primary-cta" data-console-return href="/?view=globe">Explorar la consola <span aria-hidden="true">↗</span></a></div></div>
    <div class="content-layout"><article class="article">
      <section><h2>Qué es SatLink</h2><p>SatLink Studio es una herramienta web para observar posiciones orbitales estimadas y experimentar con escenarios de seguimiento satelital. En la <a href="/?view=radar">consola</a> puedes ver múltiples objetos a la vez con Sat-Radar, seguir un satélite en un globo 3D o en un mapa 2D, calcular próximos pases para tu ubicación y explorar parámetros de enlace de radio.</p></section>
      <section><h2>Datos que se pueden entender</h2><p>El objetivo es que cada posición dibujada tenga contexto. Los elementos orbitales TLE proceden de <a href="https://celestrak.org/" target="_blank" rel="noopener noreferrer">CelesTrak</a>; SatLink los propaga mediante el modelo SGP4 para estimar posiciones en el momento de consulta. La ubicación representada no es telemetría recibida directamente del satélite. Su precisión depende, entre otros factores, de la antigüedad de los elementos y de posibles maniobras.</p><p>Las herramientas de pases y radiofrecuencia ayudan a estudiar la geometría de una estación terrestre y a probar supuestos de enlace. Sus resultados son estimaciones para explorar y aprender, no datos operacionales certificados.</p></section>
      <section><h2>Explora a tu manera</h2><div class="about-feature-grid"><a href="/?view=radar"><span>01 / OBSERVAR</span><strong>Sat-Radar</strong><small>Un mapa de los grupos disponibles con filtros y fichas orbitales.</small><b>Ir al radar ↗</b></a><a href="/?view=globe"><span>02 / SEGUIR</span><strong>Control orbital</strong><small>Trayectoria, globo 3D y posición estimada de un satélite.</small><b>Abrir globo ↗</b></a><a href="/?view=passes"><span>03 / PLANIFICAR</span><strong>Próximos pases</strong><small>Ventanas de visibilidad para la estación que elijas.</small><b>Calcular pases ↗</b></a></div></section>
      <section><h2>Proyecto abierto</h2><p>Puedes consultar el código y la evolución de SatLink en <a href="https://github.com/davidtrabancod/satlink" target="_blank" rel="noopener noreferrer">GitHub</a>. Si acabas de llegar, las <a href="/#guias">guías</a> explican las principales funciones y el alcance de los cálculos.</p></section>
    </article><aside class="aside"><div class="aside-kicker">EMPIEZA AQUÍ</div><h2>Elige una ruta</h2><p>Pasa de una vista global a una pregunta concreta sobre una órbita.</p><a href="/?view=radar">Explorar Sat-Radar <span aria-hidden="true">↗</span></a><a href="/#guias">Leer las guías <span aria-hidden="true">↗</span></a><a data-console-return href="/?view=globe">Volver a mi vista <span aria-hidden="true">←</span></a></aside></div>
    <div class="method-note"><strong>Transparencia de datos</strong><p>Las posiciones orbitales se calculan a partir de TLE públicos. La visualización continua no implica recepción en directo de señales del satélite.</p></div>
  </main>
  <footer class="site-footer"><span>© SATLINK STUDIO</span><a data-console-return href="/?view=globe">Volver a la consola ↗</a></footer>
</body>
</html>`;
await writeFile(join('public', 'seo', 'about-us.html'), aboutHtml, 'utf8');
console.log(`Generated ${pages.length} SatLink guides and About us.`);
