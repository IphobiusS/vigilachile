"""
Base de datos de comunas de Chile con coordenadas para el buscador.
Incluye las principales comunas de cada región con lat/lon para flyTo.
"""

COMMUNES = [
    # Arica y Parinacota
    {"name": "Arica", "region": "Arica y Parinacota", "region_id": "arica", "lat": -18.4783, "lon": -70.3126},
    {"name": "Putre", "region": "Arica y Parinacota", "region_id": "arica", "lat": -18.1953, "lon": -69.5586},
    {"name": "Camarones", "region": "Arica y Parinacota", "region_id": "arica", "lat": -19.0097, "lon": -69.8556},
    {"name": "General Lagos", "region": "Arica y Parinacota", "region_id": "arica", "lat": -17.7667, "lon": -69.5000},
    # Tarapacá
    {"name": "Iquique", "region": "Tarapacá", "region_id": "tarapaca", "lat": -20.2133, "lon": -70.1503},
    {"name": "Alto Hospicio", "region": "Tarapacá", "region_id": "tarapaca", "lat": -20.2690, "lon": -70.1005},
    {"name": "Pozo Almonte", "region": "Tarapacá", "region_id": "tarapaca", "lat": -20.2594, "lon": -69.7862},
    {"name": "Camiña", "region": "Tarapacá", "region_id": "tarapaca", "lat": -19.3123, "lon": -69.4233},
    {"name": "Colchane", "region": "Tarapacá", "region_id": "tarapaca", "lat": -19.2757, "lon": -68.6340},
    {"name": "Huara", "region": "Tarapacá", "region_id": "tarapaca", "lat": -19.9960, "lon": -69.7710},
    {"name": "Pica", "region": "Tarapacá", "region_id": "tarapaca", "lat": -20.4893, "lon": -69.3286},
    # Antofagasta
    {"name": "Antofagasta", "region": "Antofagasta", "region_id": "antofagasta", "lat": -23.6509, "lon": -70.3975},
    {"name": "Calama", "region": "Antofagasta", "region_id": "antofagasta", "lat": -22.4569, "lon": -68.9293},
    {"name": "Tocopilla", "region": "Antofagasta", "region_id": "antofagasta", "lat": -22.0922, "lon": -70.1979},
    {"name": "Mejillones", "region": "Antofagasta", "region_id": "antofagasta", "lat": -23.0984, "lon": -70.4528},
    {"name": "Taltal", "region": "Antofagasta", "region_id": "antofagasta", "lat": -25.4050, "lon": -70.4824},
    {"name": "San Pedro de Atacama", "region": "Antofagasta", "region_id": "antofagasta", "lat": -22.9087, "lon": -68.1997},
    {"name": "María Elena", "region": "Antofagasta", "region_id": "antofagasta", "lat": -22.3491, "lon": -69.6618},
    {"name": "Sierra Gorda", "region": "Antofagasta", "region_id": "antofagasta", "lat": -22.8940, "lon": -69.3220},
    # Atacama
    {"name": "Copiapó", "region": "Atacama", "region_id": "atacama", "lat": -27.3668, "lon": -70.3323},
    {"name": "Vallenar", "region": "Atacama", "region_id": "atacama", "lat": -28.5708, "lon": -70.7581},
    {"name": "Chañaral", "region": "Atacama", "region_id": "atacama", "lat": -26.3471, "lon": -70.6208},
    {"name": "Diego de Almagro", "region": "Atacama", "region_id": "atacama", "lat": -26.3748, "lon": -70.0508},
    {"name": "Caldera", "region": "Atacama", "region_id": "atacama", "lat": -27.0668, "lon": -70.8141},
    {"name": "Tierra Amarilla", "region": "Atacama", "region_id": "atacama", "lat": -27.4862, "lon": -70.2739},
    {"name": "Huasco", "region": "Atacama", "region_id": "atacama", "lat": -28.4672, "lon": -71.2190},
    {"name": "Freirina", "region": "Atacama", "region_id": "atacama", "lat": -28.5028, "lon": -71.0752},
    # Coquimbo
    {"name": "La Serena", "region": "Coquimbo", "region_id": "coquimbo", "lat": -29.9027, "lon": -71.2520},
    {"name": "Coquimbo", "region": "Coquimbo", "region_id": "coquimbo", "lat": -29.9533, "lon": -71.3395},
    {"name": "Ovalle", "region": "Coquimbo", "region_id": "coquimbo", "lat": -30.6010, "lon": -71.2000},
    {"name": "Illapel", "region": "Coquimbo", "region_id": "coquimbo", "lat": -31.6300, "lon": -71.1631},
    {"name": "Vicuña", "region": "Coquimbo", "region_id": "coquimbo", "lat": -30.0327, "lon": -70.7098},
    {"name": "Andacollo", "region": "Coquimbo", "region_id": "coquimbo", "lat": -30.2326, "lon": -71.0843},
    {"name": "Salamanca", "region": "Coquimbo", "region_id": "coquimbo", "lat": -31.7770, "lon": -70.9681},
    {"name": "Los Vilos", "region": "Coquimbo", "region_id": "coquimbo", "lat": -31.9125, "lon": -71.5121},
    {"name": "Combarbalá", "region": "Coquimbo", "region_id": "coquimbo", "lat": -31.1766, "lon": -71.0010},
    {"name": "Monte Patria", "region": "Coquimbo", "region_id": "coquimbo", "lat": -30.6942, "lon": -70.9597},
    # Valparaíso
    {"name": "Valparaíso", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.0472, "lon": -71.6127},
    {"name": "Viña del Mar", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.0153, "lon": -71.5500},
    {"name": "Quilpué", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.0472, "lon": -71.4428},
    {"name": "Villa Alemana", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.0422, "lon": -71.3734},
    {"name": "San Antonio", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.5933, "lon": -71.6067},
    {"name": "Quillota", "region": "Valparaíso", "region_id": "valparaiso", "lat": -32.8800, "lon": -71.2489},
    {"name": "La Calera", "region": "Valparaíso", "region_id": "valparaiso", "lat": -32.7878, "lon": -71.1984},
    {"name": "San Felipe", "region": "Valparaíso", "region_id": "valparaiso", "lat": -32.7509, "lon": -70.7264},
    {"name": "Los Andes", "region": "Valparaíso", "region_id": "valparaiso", "lat": -32.8335, "lon": -70.5984},
    {"name": "Limache", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.0015, "lon": -71.2683},
    {"name": "Concón", "region": "Valparaíso", "region_id": "valparaiso", "lat": -32.9180, "lon": -71.5315},
    {"name": "Cartagena", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.5479, "lon": -71.6032},
    {"name": "El Quisco", "region": "Valparaíso", "region_id": "valparaiso", "lat": -33.3973, "lon": -71.6925},
    {"name": "Isla de Pascua", "region": "Valparaíso", "region_id": "valparaiso", "lat": -27.1127, "lon": -109.3497},
    # Metropolitana
    {"name": "Santiago", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4489, "lon": -70.6693},
    {"name": "Puente Alto", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6117, "lon": -70.5758},
    {"name": "Maipú", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5106, "lon": -70.7574},
    {"name": "Las Condes", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4073, "lon": -70.5676},
    {"name": "La Florida", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5228, "lon": -70.5966},
    {"name": "Peñalolén", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4917, "lon": -70.5325},
    {"name": "Providencia", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4262, "lon": -70.6103},
    {"name": "Ñuñoa", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4569, "lon": -70.5974},
    {"name": "Vitacura", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.3817, "lon": -70.5714},
    {"name": "San Bernardo", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5917, "lon": -70.6997},
    {"name": "Lo Barnechea", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.3522, "lon": -70.5164},
    {"name": "Quilicura", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.3601, "lon": -70.7259},
    {"name": "Recoleta", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4041, "lon": -70.6369},
    {"name": "Estación Central", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4517, "lon": -70.6789},
    {"name": "Independencia", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4192, "lon": -70.6664},
    {"name": "Macul", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4895, "lon": -70.5994},
    {"name": "San Miguel", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4990, "lon": -70.6536},
    {"name": "La Reina", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4443, "lon": -70.5430},
    {"name": "Cerrillos", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4967, "lon": -70.7117},
    {"name": "Pedro Aguirre Cerda", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4953, "lon": -70.6750},
    {"name": "Lo Espejo", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5183, "lon": -70.6892},
    {"name": "El Bosque", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5497, "lon": -70.6653},
    {"name": "La Cisterna", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5325, "lon": -70.6594},
    {"name": "La Granja", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5350, "lon": -70.6239},
    {"name": "Renca", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4050, "lon": -70.7164},
    {"name": "Cerro Navia", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4253, "lon": -70.7322},
    {"name": "Lo Prado", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4442, "lon": -70.7244},
    {"name": "Pudahuel", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4381, "lon": -70.7497},
    {"name": "Huechuraba", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.3647, "lon": -70.6339},
    {"name": "Conchalí", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.3839, "lon": -70.6514},
    {"name": "La Pintana", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5836, "lon": -70.6336},
    {"name": "San Ramón", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5397, "lon": -70.6417},
    {"name": "San Joaquín", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.4981, "lon": -70.6286},
    {"name": "Colina", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.2026, "lon": -70.6713},
    {"name": "Lampa", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.2833, "lon": -70.8783},
    {"name": "Buin", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.7328, "lon": -70.7417},
    {"name": "Paine", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.8083, "lon": -70.7417},
    {"name": "Peñaflor", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6119, "lon": -70.8792},
    {"name": "Talagante", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6628, "lon": -70.9286},
    {"name": "Melipilla", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6864, "lon": -71.2133},
    {"name": "Isla de Maipo", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.7497, "lon": -70.9036},
    {"name": "El Monte", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6817, "lon": -71.0117},
    {"name": "Padre Hurtado", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.5714, "lon": -70.8286},
    {"name": "Calera de Tango", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6350, "lon": -70.7700},
    {"name": "Pirque", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6603, "lon": -70.5883},
    {"name": "San José de Maipo", "region": "Metropolitana", "region_id": "metropolitana", "lat": -33.6392, "lon": -70.3536},
    # O'Higgins
    {"name": "Rancagua", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.1708, "lon": -70.7408},
    {"name": "San Fernando", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.5839, "lon": -71.0008},
    {"name": "Pichilemu", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.3870, "lon": -72.0032},
    {"name": "Rengo", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.4042, "lon": -70.8622},
    {"name": "Machali", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.1800, "lon": -70.6531},
    {"name": "Graneros", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.0667, "lon": -70.7244},
    {"name": "Santa Cruz", "region": "O'Higgins", "region_id": "ohiggins", "lat": -34.6383, "lon": -71.3639},
    # Maule
    {"name": "Talca", "region": "Maule", "region_id": "maule", "lat": -35.4264, "lon": -71.6554},
    {"name": "Curicó", "region": "Maule", "region_id": "maule", "lat": -34.9831, "lon": -71.2369},
    {"name": "Linares", "region": "Maule", "region_id": "maule", "lat": -35.8467, "lon": -71.5928},
    {"name": "Constitución", "region": "Maule", "region_id": "maule", "lat": -35.3328, "lon": -72.4119},
    {"name": "Cauquenes", "region": "Maule", "region_id": "maule", "lat": -35.9667, "lon": -72.3167},
    {"name": "Molina", "region": "Maule", "region_id": "maule", "lat": -35.1156, "lon": -71.2803},
    {"name": "Parral", "region": "Maule", "region_id": "maule", "lat": -36.1397, "lon": -71.8253},
    {"name": "San Javier", "region": "Maule", "region_id": "maule", "lat": -35.5944, "lon": -71.7403},
    # Ñuble
    {"name": "Chillán", "region": "Ñuble", "region_id": "nuble", "lat": -36.6066, "lon": -72.1034},
    {"name": "Chillán Viejo", "region": "Ñuble", "region_id": "nuble", "lat": -36.6333, "lon": -72.1286},
    {"name": "San Carlos", "region": "Ñuble", "region_id": "nuble", "lat": -36.4244, "lon": -71.9589},
    {"name": "Bulnes", "region": "Ñuble", "region_id": "nuble", "lat": -36.7422, "lon": -72.2994},
    {"name": "Quirihue", "region": "Ñuble", "region_id": "nuble", "lat": -36.2808, "lon": -72.5389},
    {"name": "Coelemu", "region": "Ñuble", "region_id": "nuble", "lat": -36.4881, "lon": -72.7019},
    # Biobío
    {"name": "Concepción", "region": "Biobío", "region_id": "biobio", "lat": -36.8270, "lon": -73.0503},
    {"name": "Talcahuano", "region": "Biobío", "region_id": "biobio", "lat": -36.7253, "lon": -73.1169},
    {"name": "Los Ángeles", "region": "Biobío", "region_id": "biobio", "lat": -37.4693, "lon": -72.3527},
    {"name": "Coronel", "region": "Biobío", "region_id": "biobio", "lat": -37.0292, "lon": -73.1536},
    {"name": "Chiguayante", "region": "Biobío", "region_id": "biobio", "lat": -36.9228, "lon": -73.0292},
    {"name": "San Pedro de la Paz", "region": "Biobío", "region_id": "biobio", "lat": -36.8547, "lon": -73.1086},
    {"name": "Hualpén", "region": "Biobío", "region_id": "biobio", "lat": -36.7897, "lon": -73.0986},
    {"name": "Lota", "region": "Biobío", "region_id": "biobio", "lat": -37.0886, "lon": -73.1614},
    {"name": "Tomé", "region": "Biobío", "region_id": "biobio", "lat": -36.6175, "lon": -72.9558},
    {"name": "Penco", "region": "Biobío", "region_id": "biobio", "lat": -36.7386, "lon": -72.9953},
    {"name": "Arauco", "region": "Biobío", "region_id": "biobio", "lat": -37.2456, "lon": -73.3175},
    {"name": "Lebu", "region": "Biobío", "region_id": "biobio", "lat": -37.6114, "lon": -73.6583},
    {"name": "Mulchén", "region": "Biobío", "region_id": "biobio", "lat": -37.7172, "lon": -72.2408},
    {"name": "Nacimiento", "region": "Biobío", "region_id": "biobio", "lat": -37.5031, "lon": -72.6722},
    # Araucanía
    {"name": "Temuco", "region": "Araucanía", "region_id": "araucania", "lat": -38.7359, "lon": -72.5904},
    {"name": "Villarrica", "region": "Araucanía", "region_id": "araucania", "lat": -39.2856, "lon": -72.2279},
    {"name": "Pucón", "region": "Araucanía", "region_id": "araucania", "lat": -39.2822, "lon": -71.9544},
    {"name": "Angol", "region": "Araucanía", "region_id": "araucania", "lat": -37.7957, "lon": -72.7100},
    {"name": "Padre Las Casas", "region": "Araucanía", "region_id": "araucania", "lat": -38.7627, "lon": -72.5966},
    {"name": "Victoria", "region": "Araucanía", "region_id": "araucania", "lat": -38.2333, "lon": -72.3333},
    {"name": "Lautaro", "region": "Araucanía", "region_id": "araucania", "lat": -38.5311, "lon": -72.4253},
    {"name": "Nueva Imperial", "region": "Araucanía", "region_id": "araucania", "lat": -38.7419, "lon": -72.9533},
    {"name": "Carahue", "region": "Araucanía", "region_id": "araucania", "lat": -38.7097, "lon": -73.1714},
    # Los Ríos
    {"name": "Valdivia", "region": "Los Ríos", "region_id": "los_rios", "lat": -39.8196, "lon": -73.2452},
    {"name": "La Unión", "region": "Los Ríos", "region_id": "los_rios", "lat": -40.2939, "lon": -73.0825},
    {"name": "Panguipulli", "region": "Los Ríos", "region_id": "los_rios", "lat": -39.6436, "lon": -72.3350},
    {"name": "Río Bueno", "region": "Los Ríos", "region_id": "los_rios", "lat": -40.3339, "lon": -72.9567},
    {"name": "Lago Ranco", "region": "Los Ríos", "region_id": "los_rios", "lat": -40.3153, "lon": -72.5022},
    {"name": "Máfil", "region": "Los Ríos", "region_id": "los_rios", "lat": -39.6614, "lon": -72.9517},
    {"name": "Corral", "region": "Los Ríos", "region_id": "los_rios", "lat": -39.8856, "lon": -73.4325},
    # Los Lagos
    {"name": "Puerto Montt", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.4689, "lon": -72.9411},
    {"name": "Castro", "region": "Los Lagos", "region_id": "los_lagos", "lat": -42.4800, "lon": -73.7622},
    {"name": "Osorno", "region": "Los Lagos", "region_id": "los_lagos", "lat": -40.5736, "lon": -73.1355},
    {"name": "Puerto Varas", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.3191, "lon": -72.9834},
    {"name": "Ancud", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.8680, "lon": -73.8281},
    {"name": "Quellón", "region": "Los Lagos", "region_id": "los_lagos", "lat": -43.1158, "lon": -73.6150},
    {"name": "Dalcahue", "region": "Los Lagos", "region_id": "los_lagos", "lat": -42.3797, "lon": -73.6467},
    {"name": "Frutillar", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.1228, "lon": -73.0636},
    {"name": "Llanquihue", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.2581, "lon": -73.0014},
    {"name": "Calbuco", "region": "Los Lagos", "region_id": "los_lagos", "lat": -41.7714, "lon": -73.1311},
    {"name": "Purranque", "region": "Los Lagos", "region_id": "los_lagos", "lat": -40.9072, "lon": -73.1664},
    {"name": "Río Negro", "region": "Los Lagos", "region_id": "los_lagos", "lat": -40.7833, "lon": -73.2167},
    {"name": "Chaitén", "region": "Los Lagos", "region_id": "los_lagos", "lat": -42.9167, "lon": -72.7097},
    # Aysén
    {"name": "Coyhaique", "region": "Aysén", "region_id": "aysen", "lat": -45.5712, "lon": -72.0685},
    {"name": "Aysén", "region": "Aysén", "region_id": "aysen", "lat": -45.4000, "lon": -72.6833},
    {"name": "Chile Chico", "region": "Aysén", "region_id": "aysen", "lat": -46.5397, "lon": -71.7233},
    {"name": "Cochrane", "region": "Aysén", "region_id": "aysen", "lat": -47.2544, "lon": -72.5758},
    # Magallanes
    {"name": "Punta Arenas", "region": "Magallanes", "region_id": "magallanes", "lat": -53.1548, "lon": -70.9113},
    {"name": "Puerto Natales", "region": "Magallanes", "region_id": "magallanes", "lat": -51.7311, "lon": -72.4869},
    {"name": "Porvenir", "region": "Magallanes", "region_id": "magallanes", "lat": -53.2975, "lon": -70.3628},
    {"name": "Puerto Williams", "region": "Magallanes", "region_id": "magallanes", "lat": -54.9333, "lon": -67.6167},
]


def search_communes(query: str, limit: int = 10):
    """
    Búsqueda fuzzy de comunas por nombre, región o localidad.
    Normaliza acentos y es case-insensitive.
    """
    if not query or len(query.strip()) < 2:
        return {"results": []}

    query_norm = normalize(query.strip().lower())
    scored = []

    for c in COMMUNES:
        name_norm = normalize(c["name"].lower())
        region_norm = normalize(c["region"].lower())

        # Match exacto al inicio del nombre — prioridad máxima
        if name_norm.startswith(query_norm):
            scored.append((0, c))
        # Match parcial en nombre
        elif query_norm in name_norm:
            scored.append((1, c))
        # Match en región
        elif query_norm in region_norm:
            scored.append((2, c))
        # Match fuzzy — al menos 70% de las letras del query están en el nombre
        elif fuzzy_match(query_norm, name_norm):
            scored.append((3, c))

    # Ordenar por score y limitar
    scored.sort(key=lambda x: (x[0], x[1]["name"]))
    results = [item[1] for item in scored[:limit]]

    return {"results": results}


def normalize(text: str) -> str:
    """Eliminar acentos para búsqueda más flexible."""
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def fuzzy_match(query: str, target: str) -> bool:
    """Match fuzzy simple: al menos 70% de caracteres del query presentes en orden."""
    if len(query) < 3:
        return False
    matches = 0
    idx = 0
    for char in query:
        found = target.find(char, idx)
        if found >= 0:
            matches += 1
            idx = found + 1
    return matches / len(query) >= 0.7
