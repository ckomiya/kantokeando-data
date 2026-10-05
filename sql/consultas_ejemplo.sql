-- Consultas de ejemplo para validar el esquema (ver sql/schema.sql).
-- Cubren los casos de uso de la aplicación web (solo lectura).

-- 1) Torneos realizados por año.
SELECT anio, count(*) AS cantidad_torneos
FROM torneos
GROUP BY anio
ORDER BY anio DESC;

-- 2) Torneos de un año específico, con su categoría/resultados resumidos.
SELECT id_torneo, nombre_torneo, nombre_comun, fecha_torneo, lugar, url
FROM torneos
WHERE anio = 2025
ORDER BY fecha_torneo DESC;

-- 3) Listar torneos por nombre común, mostrando el año para diferenciarlos
--    (ej. "Campeonato Metropolitano" se repite varias veces).
SELECT anio, nombre_torneo, fecha_torneo, url
FROM torneos
WHERE nombre_comun = 'Campeonato Metropolitano'
ORDER BY fecha_torneo DESC;

-- 3b) Mismo caso, pero agrupando como lo mostraría la UI: "(2025) Campeonato Metropolitano".
SELECT anio || ' - ' || nombre_comun AS etiqueta, fecha_torneo, nombre_torneo, url
FROM torneos
WHERE nombre_comun = 'Campeonato Metropolitano'
ORDER BY fecha_torneo DESC;

-- 4) Buscar jugador y ver sus estadísticas: torneos donde participó,
--    ordenados de más reciente a más antiguo, con el puesto obtenido y el link.
SELECT
    t.fecha_torneo,
    t.anio,
    t.nombre_torneo,
    t.nombre_comun,
    r.categoria,
    e.nombre_equipo,
    r.puesto,
    t.url
FROM jugadores j
JOIN resultado_jugadores rj ON rj.id_jugador = j.id_jugador
JOIN resultados r ON r.id_resultado = rj.id_resultado
JOIN torneos t ON t.id_torneo = r.id_torneo
LEFT JOIN equipos e ON e.id_equipo = r.id_equipo
WHERE j.nombre_canonico = 'Luis Sakugawa'
ORDER BY t.fecha_torneo DESC;

-- 4b) Resumen de estadísticas del jugador: cantidad de participaciones y de 1eros puestos.
SELECT
    j.nombre_canonico,
    count(*) AS participaciones,
    count(*) FILTER (WHERE r.puesto = 1) AS primeros_puestos,
    min(t.fecha_torneo) AS primera_participacion,
    max(t.fecha_torneo) AS ultima_participacion
FROM jugadores j
JOIN resultado_jugadores rj ON rj.id_jugador = j.id_jugador
JOIN resultados r ON r.id_resultado = rj.id_resultado
JOIN torneos t ON t.id_torneo = r.id_torneo
WHERE j.nombre_canonico = 'Luis Sakugawa'
GROUP BY j.nombre_canonico;

-- 5) Buscar jugador por coincidencia parcial (autocompletar en la UI).
SELECT id_jugador, nombre_canonico
FROM jugadores
WHERE nombre_canonico ILIKE '%sakugawa%'
ORDER BY nombre_canonico;

-- 6) Estadísticas por equipo: torneos donde participó un equipo y el puesto obtenido.
SELECT
    t.fecha_torneo,
    t.nombre_torneo,
    r.categoria,
    r.puesto,
    t.url
FROM equipos e
JOIN resultados r ON r.id_equipo = e.id_equipo
JOIN torneos t ON t.id_torneo = r.id_torneo
WHERE e.nombre_equipo = 'AELU 3'
ORDER BY t.fecha_torneo DESC;

-- 7) Jugadores que integraron un resultado/equipo específico (para mostrar el roster).
SELECT j.nombre_canonico
FROM resultado_jugadores rj
JOIN jugadores j ON j.id_jugador = rj.id_jugador
WHERE rj.id_resultado = 1
ORDER BY j.nombre_canonico;

-- 8) Detalle completo de un torneo: todas sus categorías/equipos/jugadores.
SELECT
    r.categoria,
    r.puesto,
    e.nombre_equipo,
    string_agg(j.nombre_canonico, ', ' ORDER BY j.nombre_canonico) AS jugadores
FROM resultados r
LEFT JOIN equipos e ON e.id_equipo = r.id_equipo
LEFT JOIN resultado_jugadores rj ON rj.id_resultado = r.id_resultado
LEFT JOIN jugadores j ON j.id_jugador = rj.id_jugador
WHERE r.id_torneo = '2024-11-18-copa-jose-watanabe-kaway'
GROUP BY r.id_resultado, r.categoria, r.puesto, e.nombre_equipo
ORDER BY r.categoria, r.puesto;
