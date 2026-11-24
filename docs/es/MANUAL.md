# Guyrapu, manual de uso

Guyrapu lee en voz alta el chat de los directos de YouTube y TikTok, y
maneja OBS Studio y Restream desde el teclado. Está pensado para personas
ciegas o con baja visión que transmiten, y se prueba con NVDA.

Versión 3.0.0 beta 9 · Windows 10 y 11 · [Novedades](CHANGELOG.md)

## Instalación

Descomprime el ZIP en cualquier carpeta y abre `Guyrapu.exe`. No hace falta
instalar nada ni tener permisos de administrador.

Se necesita Windows 10 u 11, conexión a internet y al menos una voz de
Windows, que se agrega en *Configuración, Hora e idioma, Voz*. ElevenLabs es
opcional y requiere una cuenta propia.

## La ventana principal

Al abrir Guyrapu, el foco está en el campo *Enlace o ID*. Pega el enlace de
un directo o de un vídeo y pulsa *Conectar*. La lista *Recientes* ofrece los
directos que ya abriste.

La ventana tiene tres regiones: *Conexión*, *Contenido* y *Reproductor*. En
*Contenido* están las pestañas *Chat del directo*, *Comentarios* e
*Información*. Cada cambio de región o de pestaña se anuncia.

Los comandos del menú que abren un cuadro terminan en puntos suspensivos.
*Ir al chat del directo*, *Ir a comentarios* e *Ir al reproductor* se escriben en
minúscula después de «Ir a». Los cuadros de prueba tienen el botón *Iniciar*,
y en música el comando es *Cambiar nombre de la lista*. Los botones *Cancelar*
y *Cerrar* tienen letra de acceso, como el resto de los comandos.

`F1` abre el manual en la sección de la ventana abierta. Cuando abres el
historial, OBS, Restream o los ajustes de perfil, el foco queda en el primer
control útil.

Los botones y las listas que están cargando o esperando siguen en el recorrido
con `Tab` y dicen qué pasa: *Cargar listas* dice que está cargando, *Capturar*
dice si carga las fuentes o está capturando, *Enviar* dice que espera,
*Comprobar clave* dice que se está comprobando, y *Calidad* dice
cuando el formato no tiene calidad. *Aceptar* dice por qué no hay nada para
elegir en los cuadros de fuentes, y una lista vacía dice por qué. Las acciones
de OBS sin conexión siguen en el recorrido, dicen «sin conexión con OBS» y al
pulsarlas avisan que OBS no está conectado. Con un chat conectado, el campo
del enlace sigue en el recorrido con `Tab` y se puede leer; para cambiarlo hay
que desconectar. Las esperas suenan mientras duran y suenan listo o error al
terminar.

| Tecla en la lista Recientes | Acción |
|---|---|
| `Intro` | Abrir el directo |
| `Supr` | Eliminarlo del historial |

## <a id="chat"></a>El chat

Cada mensaje se lee con la voz elegida y lleva un sonido según quién
escribe (propietario del canal, moderador, cuenta verificada o miembro) y
según lo que es (Super Chat, membresía o regalo de TikTok). Los Super Chats y
los stickers de YouTube suenan según su monto, con los mismos tres sonidos de
los regalos de TikTok: chico, mediano y grande.

Con *Traducir chat*, en el menú *Chat* y en *Preferencias*, categoría
*Lectura*, los mensajes en otro idioma se leen y se muestran traducidos, con
el idioma original al final. Viene desactivada.

Si el chat se interrumpe solo en pleno directo, suena como una desconexión, y
al volver, como una reconexión. Es distinto de conectarlo o desconectarlo a
mano.

En la lista del chat, las flechas pasan de un mensaje a otro, y al escribir
unas letras el foco salta al primer autor que empieza así. El menú
contextual copia el mensaje, silencia al autor durante la sesión y le asigna
un alias. Con la sesión de Google iniciada, también suspende al autor o lo
oculta del canal. Al llegar al principio o al final suena un aviso. El menú
muestra la tecla de cada acción y `Mayús+F10` también lo abre.

Los mensajes que son un comando, como `!discord`, o un voto, como `!1`, tienen
su propio modo de lectura en *Preferencias*, categoría *Eventos del directo*.
De fábrica se ven en la lista sin leerse.

Cuando el chat va lleno, el aviso de mensajes descartados dice que los
mensajes están en la lista del chat y que `F10` sube la velocidad de la voz
para seguir el ritmo. No recomienda leer solo el nombre.

*Buscar en el chat…*, en el menú *Chat* o con `Alt+B`, encuentra un texto en
los mensajes del directo y lleva al mensaje. *Participación en el chat…*, en
el mismo menú o con `Alt+P`, muestra cuántos mensajes escribió cada persona,
suma sus regalos y Super Chats y permite ordenar por regalos y guardar el
resumen como texto, para agradecer al terminar el directo.

En TikTok, Guyrapu solo lee: TikTok no ofrece una forma oficial de comentar
ni de moderar. Los nombres con letras decorativas se leen como texto normal,
cada persona que sigue se anuncia una sola vez por directo y al reconectar no
se repiten comentarios.

Con un perfil de Restream que lee el chat de YouTube y el de TikTok, los dos
llegan a la misma lista y cada fila dice de qué plataforma es. Al empezar el
directo, el chat de TikTok puede tardar en conectarse: Guyrapu espera hasta
3 minutos y avisa una vez que TikTok todavía no deja leer el chat. En
*Preferencias*, categoría *Eventos del directo*, *Sonido propio de cada
plataforma* elige si los mensajes de TikTok tienen su sonido siempre, solo
con varios chats o nunca, y *Anunciar qué plataforma tiene cada mensaje
cuando hay varios chats* hace que la voz también lo diga.

### Eventos del directo

Las entradas, los me gusta, los seguidores, los regalos, las encuestas, las
metas y las batallas de TikTok se configuran en *Preferencias*, categoría
*Eventos del directo*. Cada evento tiene una lista con estos modos:

- *Voz principal y sonido* y *Voz secundaria y sonido*: aparece en la
  lista, suena y se lee con esa voz.
- *Voz principal sin sonido* y *Voz secundaria sin sonido*: aparece y se
  lee con esa voz, sin su sonido.
- *Solo sonido*: aparece y suena, sin leerse.
- *Solo en la lista*: aparece sin sonido y sin leerse.
- *Desactivado*: no aparece.

*Agrupar entradas* y *Agrupar me gusta* juntan en una fila lo que llega en
pocos segundos, como «Ana, Beto y Caro entraron».

### Formato de lectura

El formato decide qué parte del mensaje se lee. Se elige en *Preferencias*,
categoría *Lectura*.

| Formato | Ejemplo |
|---|---|
| Nombre y mensaje | «Lucía: hola a todos» |
| Mensaje y después el nombre | «hola a todos, de Lucía» |
| Solo el mensaje | «hola a todos» |
| Solo el nombre | «Lucía» |

Las palabras y los usuarios que no se leen se escriben en la categoría
*Filtros*.

### Alias

Un alias cambia cómo se lee el nombre de un autor, por ejemplo uno hecho de
letras y números. En el menú contextual de un mensaje, elige *Asignar alias
a <autor>…*. El alias vale también para los mensajes anteriores, y la
moderación sigue actuando sobre la cuenta real. Para eliminarlo, deja el
campo vacío.

### Escribir en el chat

El cuadro *Mensaje* está después de la lista del chat. Para escribir hace
falta la sesión de Google y un directo de YouTube con el chat abierto. Si
falta algo, el botón *Enviar* lo dice en su nombre. Cada mensaje admite
hasta 200 caracteres.

| Tecla en el cuadro Mensaje | Acción |
|---|---|
| `Intro` | Enviar el mensaje |
| `Mayús+Intro` | Insertar un salto de línea |

En un vídeo publicado, la pestaña *Comentarios* lee los comentarios, y con
la sesión de Google permite comentar y responder. *Cargar más* y *Recargar
comentarios* se alcanzan siempre con `Tab` y dicen por qué no pueden hacer
nada. En la
lista, *Responder…* aparece siempre: sin sesión de Google dice por qué no se
puede usar, y `Mayús+F10` abre el menú con la tecla de cada acción.

## <a id="voces"></a>Voces y sonidos

Guyrapu lee con SAPI 5 y OneCore, que vienen con Windows, y con ElevenLabs,
que requiere una cuenta. Las voces de Phonon y de Piper se instalan desde
*Administrar voces*, en el menú *Voz* o desde el botón del mismo nombre en
*Preferencias*, categoría *Voces*, y aparecen en esa categoría una vez
instaladas. El motor y la voz se eligen ahí. La velocidad, el volumen y el
tono se ajustan con deslizadores anchos, como el
deslizador del volumen de la música y el de los medios. *Probar voz* reproduce
una muestra con cualquier motor. Las voces locales dicen su idioma. La voz secundaria puede
usar otro motor. Si una voz local falla o ElevenLabs falla por la red o por
falta de saldo, Guyrapu lee con la *Voz de Windows de respaldo* y lo avisa una
vez. Con Phonon o Piper se elige
también la salida de audio de la voz del chat, por ejemplo los auriculares,
para que no entre al directo. La voz se elige en *Preferencias*, categoría
*Voces*: el menú *Voz* no tiene submenú para elegir voz.

Cada tipo de mensaje, evento y aviso tiene su sonido. En la categoría
*Sonidos* se elige el tema, *Predeterminado* o *Suave*, y se desactiva cada
sonido por separado. La página muestra los sonidos agrupados por familia y
dice la familia de cada uno. Tiene menú contextual con *Reproducir sonido*,
suena al llegar al borde con las flechas y busca al teclear, como las demás
listas. En inglés, los nombres salen traducidos. Las esperas suenan mientras
duran y suenan listo o error al terminar: cargar las listas del directo de
YouTube, agregar una captura a la IA, pedir el micrófono a OBS, conectar
Restream, iniciar sesión en YouTube, comprobar claves en *Preferencias*,
cargar la carpeta de música y buscar actualizaciones. El sonido de espera suena
al conectar y en las demás esperas, y no se parece al de desconectado.

*Licencias de las voces*, en el menú *Ayuda*, abre en el navegador la licencia
de cada paquete de voces que se puede descargar.

### Administrar voces

*Administrar voces…*, en el menú *Voz*, abre la ventana del mismo nombre.
También se abre desde el botón *Administrar voces…* de *Preferencias*,
categoría *Voces*. Con `Tab` se recorren los controles en este orden:
*Idioma*, *Motor de voz*, *Buscar voz*, *Voces*, *Detalles*, *Instalar*,
*Actualizar*, *Eliminar*, *Vista previa de voz* y *Cerrar*. En *Buscar voz*,
la flecha abajo baja a la lista de voces sin salir del cuadro. En *Voces* la
selección es múltiple: `Intro` oye la vista previa y `Supr` elimina los
paquetes elegidos.

Para instalar una o varias voces, selecciónalas en *Voces* y pulsa *Instalar*.
Las voces elegidas se descargan e instalan juntas, con una sola espera que
se puede cancelar. Con Phonon se instalan todas las voces del idioma juntas,
porque el paquete es el idioma entero. *Actualizar* y *Eliminar* actúan sobre
los paquetes ya instalados, y *Eliminar* pide confirmación.

Cada fila de *Voces* dice el nombre de la voz, su género, su idioma, la
calidad o la edad que publica el motor, el estado del paquete y un aviso
cuando la licencia limita el uso. *Detalles* muestra el nombre del paquete,
el motor, la calidad de cada voz de Piper, la edad de cada voz de Phonon, el
idioma, la cantidad de voces, el tamaño, el estado, la licencia y el uso.
La calidad de Piper puede ser muy baja, baja, media o alta. La edad de
Phonon puede ser joven, adulto joven, adulto, mediana edad o adulto mayor.

El uso de cada paquete aparece en la fila como aviso y en *Detalles* con una
frase: «Uso: libre, también comercial.», «Uso: solo no comercial. Un directo
con ingresos es uso comercial.», «Uso: solo investigación. La voz parte de
datos con licencia de investigación.» o «Uso: sin confirmar. La ficha de la
voz no indica su licencia o de qué datos parte.». La licencia de cada
paquete está en *Detalles*, con su enlace, y en *Licencias de las voces*, del
menú *Ayuda*.

*Vista previa de voz* reproduce la muestra de la voz elegida, igual que
`Intro` en la lista. En Phonon, la vista previa usa la muestra más larga de
cada voz.

### Las familias de sonidos

Las familias aparecen en este orden, y cada una dice qué clase de aviso
suena con ella:

- *Completado*: lo que pediste salió bien. *Texto copiado* suena con
  `copiar.wav`, y el resto de la familia usa el mismo archivo: *Acción
  completada*, *Voz cambiada*, *Mensaje enviado*, *Comentario publicado*,
  *Acción de moderación*, *Cola de lectura vaciada*, *Clip guardado*,
  *Captura agregada*, *Búsqueda con resultados*, *Búsqueda sin resultados*,
  *Descarga agregada a la cola* y *Actualización lista para instalar*.
- *Error*: lo que pediste no se pudo hacer. *Error* suena con `error.wav`, y
  el resto de la familia usa el mismo archivo: *Error de la IA*, *Búsqueda
  fallida*, *Formatos no disponibles* y *Captura negra detectada*.
- *En curso*: algo está en marcha o en espera. *Espera* suena con
  `espera.wav`, y el resto de la familia usa el mismo archivo: *Conexión en
  curso*, *Reproductor ocupado*, *Consulta enviada a la IA*, *Búsqueda en
  curso*, *Carga de formatos*, *TikTok limita las consultas* y *Preparación
  de la transmisión*.
- *Activado*: algo se activa o vuelve. *Lectura reanudada* suena con
  `reanudar.wav`, y *Conexión establecida*, *Grabación iniciada* y
  *Grabación reanudada* usan el mismo archivo.
- *Desactivado*: algo se desactiva o se detiene. *Lectura en pausa* suena con
  `pausa.wav`, y el resto de la familia usa el mismo archivo: *Desconexión
  del chat*, *Grabación detenida*, *Grabación en pausa*, *Consulta a la IA
  cancelada* y *Descarga cancelada*.
- *Advertencia*: conviene mirar algo. *Aviso general* suena con `aviso.wav`,
  y el resto de la familia usa el mismo archivo: *Problema de la grabación*,
  *Otros destinos de Restream*, *Atajos globales ocupados* y *Señal débil en
  Restream*.
- *Desconexión*: algo en directo se interrumpe o deja de responder. *Problema de la
  transmisión* suena con `transmision_problema.wav`, y el resto de la familia
  usa el mismo archivo: *Reconexión del directo*, *Directo con cortes
  seguidos*, *Destino de Restream desconectado*, *Restream sin señal*, *Chat
  desconectado*, *OBS no responde* y *Reproducción interrumpida*.
- *Reconexión*: eso mismo vuelve. *Transmisión recuperada* suena con
  `transmision_recuperada.wav`, y el resto de la familia usa el mismo
  archivo: *Destino de Restream de vuelta*, *Señal de Restream recuperada*,
  *Chat reconectado* y *OBS vuelve a responder*.
- *Transmisión y directo*: el estado de la transmisión y del directo. *Directo
  en curso* suena con `al_aire.wav`, *Transmisión detenida* con
  `transmision_detenida.wav`, *Fin del directo* con `fin_directo.wav`, *Directo
  de TikTok en pausa* con `directo_pausado.wav` y *Directo de TikTok
  continúa* con `directo_reanudado.wav`. *Cierre confirmado del directo* y
  *Reproducción finalizada* usan el de su familia, `fin_directo.wav`.
- *Chat*: los mensajes y los eventos del chat. *Mensaje nuevo del chat* suena
  con `mensaje_nuevo.wav`, *Mensaje de TikTok* con `mensaje_tiktok.wav`,
  *Mensaje del propietario del canal* con `mensaje_propietario.wav`,
  *Mensaje del moderador* con `mensaje_moderador.wav`, *Mensaje de una cuenta
  verificada* con `mensaje_verificado.wav`, *Mensaje de un miembro del canal*
  con `mensaje_miembro.wav`, *Super Chat* con `superchat.wav`, *Nuevo miembro
  del canal* con `nuevo_miembro.wav`, *Nuevo seguidor del directo* con
  `seguir.wav`, *Alguien compartió el directo* con `compartir.wav`, *Cofre de
  regalos recibido* con `cofre.wav`, *Me gusta del directo* con `me_gusta.wav`,
  *Regalo o Super Chat chico* con `regalo_chico.wav`, *Regalo o Super Chat
  mediano* con `regalo_mediano.wav`, *Regalo o Super Chat grande* con
  `regalo_grande.wav`,
  *Alguien entró al directo* con `entrada.wav`, *Encuesta abierta* con
  `encuesta.wav`, *Encuesta terminada* con `encuesta_fin.wav`, *Meta cumplida*
  con `meta.wav`, *Batalla iniciada* con `batalla.wav` y *Batalla terminada*
  con `batalla_fin.wav`.
- *Descargas*: el avance y el resultado de las descargas. *Avance de
  descarga* suena con `descarga_avance.wav`, y *Descarga iniciada* y
  *Procesamiento de descarga* usan el mismo archivo. *Descarga quieta* suena
  con `descarga_quieta.wav`, *Descarga completada* con
  `descarga_completada.wav`, *Descarga fallida* con `descarga_fallida.wav`,
  *Descarga parcial* usa `descarga_fallida.wav` y *Cola de descargas
  terminada* suena con `cola_descargas_terminada.wav`.
- *Inteligencia artificial*: las consultas y las respuestas de la IA. *La IA
  está analizando* suena con `ia_analizando.wav` y *Respuesta de la IA* con
  `ia_respuesta.wav`.
- *Música*: lo que pasa con las canciones. *Canción cambiada* suena con
  `musica_tema.wav`, *Fin de la cola de música* con `musica_fin.wav`, *Error
  al reproducir la canción* con `musica_fallo.wav`, *Igualación del volumen*
  con `musica_igualando.wav` y *Igualación del volumen completada* con
  `musica_igualada.wav`. *Canción cambiada* se ajusta en *Preferencias*,
  categoría *Sonidos*, y no en *Música*. Quien la tenía marcada sigue oyéndola;
  en las instalaciones nuevas, ese sonido y el del fin de la cola de música
  vienen desactivados.
- *Indicadores*: los avisos de las listas, el encuadre y el micrófono.
  *Principio o final de una lista* suena con `orilla.wav`, *Rostro fuera del
  encuadre* con `encuadre_fuera.wav`, *Rostro de vuelta en el encuadre* con
  `encuadre_dentro.wav`, *Micrófono con buen nivel* con `microfono_bien.wav`,
  *Nivel del micrófono para revisar* con `microfono_revisar.wav` y *Micrófono
  sin señal* con `microfono_sin_senal.wav`.
- *Aplicación*: el inicio de Guyrapu y las actualizaciones. *Inicio de la
  aplicación* suena con `app_inicio.wav` y *Actualización disponible* con
  `actualizacion_disponible.wav`.

### Un tema propio

Para armar un tema propio, copia la carpeta `sounds/themes/default` con otro
nombre. Un archivo con el nombre de un evento suena para ese evento, por
ejemplo `superchat.wav`. Si el tema no trae ese archivo, suena el de su
familia dentro del mismo tema y, si tampoco está, el del tema predeterminado.
Así puedes cambiar solo los sonidos que quieras.

## Reproductor

El vídeo del directo se reproduce dentro de Guyrapu, con los comandos del
menú *Reproductor*. En un directo, cada salto dice la distancia al directo,
por ejemplo «40 segundos por detrás del directo», y en YouTube se puede
retroceder hasta una hora. Si la conexión falla, Guyrapu reconecta en el
mismo punto. Si el proceso que une el vídeo y el audio se cae, lo vuelve a
abrir solo y sigue reproduciendo en vez de quedarse en silencio.

Con el foco en el vídeo, las teclas del `0` al `9` llevan la posición al 0,
10, 20 y así hasta el 90 % del vídeo, como en YouTube. Guyrapu anuncia la
posición a la que se movió.

*Reproducir solo el audio, sin imagen*, en *Preferencias*, categoría
*Reproductor*, viene marcada: sin imagen, los saltos son casi inmediatos.

## <a id="musica"></a>Música

Guyrapu reproduce música mientras transmites. Usa la carpeta Música que
está junto a la aplicación, o la que elijas en *Preferencias*, categoría
*Música*. Los comandos están en el menú *Música*, y *Elegir música…* abre
la ventana *Música*:

- *Colecciones* muestra la *Biblioteca*, que es tu carpeta, y tus listas.
- *Buscar* filtra mientras escribes, también sin tildes.
- *Canciones* tiene un menú contextual para reproducir ahora, a
  continuación o hasta el final, y para agregar a la cola o a una lista.
- *Mostrar cola* muestra lo que va a sonar.
- *Abrir enlace…* agrega a la cola un vídeo o una lista de YouTube.

En *Canciones*, en la cola y en los resultados del buscador se pueden elegir
varias canciones con `Mayús` y las flechas, `Ctrl+Espacio` o `Ctrl+A`.
*Reproducir*, *Agregar a la cola*, *Agregar a la lista* y *Eliminar* actúan
sobre todas con un solo anuncio. Las acciones que piden una sola fila siguen
en el menú y dicen por qué no se pueden usar. `F2` cambia el nombre de la
lista elegida en *Colecciones*. Volver a escuchar un tema de YouTube empieza
al instante. Si un tema no abre con la dirección guardada, Guyrapu la vuelve
a pedir antes de saltarlo.

*Silenciar música*, en el menú *Música*, hace lo mismo que `Ctrl+Alt+M`. Con
*Usar teclas multimedia del teclado*, las teclas de reproducir, pausar y
canción siguiente o anterior manejan la música mientras haya temas en la
cola, y el panel de medios de Windows muestra qué suena. Se desactiva en
*Preferencias*, categoría *Música*.

Al crear o editar una lista se abre un cuadro con dos listas. En
*Canciones de la lista*, `Supr` quita la canción y `Alt+Flecha arriba` y
`Alt+Flecha abajo` la mueven. *Todas las canciones* muestra la carpeta con
una casilla por canción, marcada en las que ya están en la lista: al
marcarla o desmarcarla, la canción se agrega o se quita. Su menú tiene la
tecla Aplicaciones y *Agregar todas a la lista*, que suma de una vez las
canciones que muestra la búsqueda, y `Ctrl+A` selecciona todas. En las dos
listas, `Intro` reproduce la canción.

El volumen de la música se ajusta con un deslizador en *Preferencias*,
categoría *Música*, igual que el volumen del reproductor. En esa misma
categoría, *Bajar música mientras habla la voz* y *Bajar música mientras
suena un medio* bajan la música sola mientras pasa una de esas cosas, y
*Volumen de la música al bajarla* fija el volumen al que baja. De fábrica baja
con los medios y no con la voz.

*Igualar volumen de las canciones* hace que todas suenen con un volumen
parecido. Cada archivo se mide una vez, con el botón *Igualar volumen* de
la ventana *Música*, y no se modifica. Al terminar, suena un sonido y dice
cuántas canciones quedaron igualadas. Al abrir Música, el cuadro que propone
igualar tiene el botón *No volver a preguntar*. Entre una canción y la
siguiente hay un fundido, que se ajusta en *Fundido entre canciones, en
segundos*.

Con *Usar atajos de música en cualquier aplicación*, los atajos de música
funcionan también en OBS o en un juego, y esas teclas dejan de llegar a las
demás aplicaciones.

Donde NVDA detecta una tabla, como en el Explorador de archivos, se queda
con Ctrl+Alt y las flechas. En ese caso, pulsa NVDA+F2 antes del atajo.

## Transmitir en directo

Guyrapu inicia y finaliza el directo con OBS Studio, hacia YouTube o hacia
varias plataformas a la vez con Restream.

### Antes de transmitir por primera vez

- Activa el servidor WebSocket de OBS en *Preferencias*, categoría *OBS*.
- Para YouTube, inicia la sesión de Google y activa los directos en tu
  canal.
- Para Restream, conecta la cuenta y crea un perfil. Consulta
  [Restream](#restream).
- Para que OBS use un perfil distinto al transmitir en horizontal, en
  vertical o al grabar, asígnalos en la pestaña *Perfiles* del *Panel de
  OBS*. Consulta [Perfiles de OBS](#perfiles-de-obs).

Si OBS está cerrado, Guyrapu lo abre en el área de notificación. Antes de
transmitir, si la cortina de pantalla de NVDA dejaría negra una captura de
pantalla, Guyrapu lo avisa, dice cómo arreglarlo y ofrece cambiar el método
de captura a Windows 10.

### <a id="transmitir"></a>Iniciar el directo

1. Pulsa *Transmitir en directo*, junto a *Conectar*. Se abre el cuadro
   *Transmitir a*, con el destino de la vez anterior ya elegido.
2. Elige *YouTube* o un perfil de Restream y pulsa *Continuar*.
3. Guyrapu prepara OBS y revisa la escena: si está vacía, si una imagen
   sale en negro o si el micrófono está silenciado. Si eliges *TikTok* y el
   perfil de OBS no tiene clave de transmisión, lo avisa y dice dónde
   escribirla en OBS. Si encuentra un
   problema, el botón elegido de entrada es *Cancelar*. Si transmites a
   TikTok y la cuenta de Restream también va a mandar el directo a otros
   destinos encendidos, la confirmación lo dice antes de empezar, con un
   sonido propio y el foco en *Cancelar*, y sugiere elegir un perfil de
   Restream. Si algo falla al iniciar, el error sale siempre en un cuadro.
4. Para YouTube, o un perfil con YouTube, escribe el título, la
   descripción y la privacidad. El resto de los datos es opcional, y
   Guyrapu recuerda lo último que escribiste. Para hacer pruebas, usa *No
   listado*.
5. Cuando el directo empieza, Guyrapu conecta el chat y lo anuncia.

Si se pierde la conexión a internet, YouTube espera a que vuelva sin
terminar el directo. Cerrar Guyrapu no interrumpe el directo, y al volver a
abrirlo lo reconoce. Si Guyrapu se cerró sin conexión con un directo de
YouTube abierto, al volver lo avisa y lo finaliza solo cuando vuelve la
conexión, aunque la aplicación siga cerrada. Cuando transmites a YouTube y
TikTok a la vez, *Copiar enlace del directo* copia los dos enlaces, uno
debajo del otro.

Durante el directo, el botón se llama *Finalizar directo* y pide
confirmación, con *Seguir transmitiendo* elegido de entrada. Al terminar,
Guyrapu dice cuántos fotogramas se perdieron, si fue por la red, por el
codificador o por el dibujo de la escena, y qué cambiar en el perfil para
el próximo. OBS vuelve al perfil que tenía antes del directo, también si lo
cancelas antes de empezar.

### <a id="microfono"></a>Micrófono

*Silenciar micrófono de OBS*, en el menú *OBS*, silencia o activa el
micrófono. Al activarlo, Guyrapu dice qué dispositivo usa y avisa si no
entra sonido. Para fijar el dispositivo, usa *Elegir micrófono…* en la
pestaña *Audio* del *Panel de OBS*.

### Grabar y guardar clips

Con *Grabar también al transmitir* marcada, en el menú *Transmisión*, OBS
graba mientras dura el directo. Si la grabación no se puede iniciar, el
directo sigue y suena un aviso. Para grabar sin transmitir, usa el menú
*OBS* o la pestaña *Grabación* del *Panel de OBS*.

*Guardar clip* guarda los últimos 30 o 60 segundos, según la lista *Clips*
de *Preferencias*, categoría *OBS*. Con *Permitir !clip en el chat*,
cualquiera del chat guarda un clip escribiendo `!clip`, con una espera
entre clips que se elige en la misma categoría.

Al detener una grabación o guardar un clip, Guyrapu dice el nombre del
archivo.

### Chat en el vídeo

El chat en el vídeo muestra los mensajes y los regalos sobre la imagen del
directo, para los espectadores, con un color por persona. Se agrega con
*Agregar fuente…*, *Chat en el vídeo…*, en la pestaña *Escena* del *Panel
de OBS*. En otra aplicación de transmisión, como Streamlabs, se agrega como
fuente de navegador con este enlace:

    http://127.0.0.1:8730/chat

## <a id="panel-obs"></a>Panel de OBS

El *Panel de OBS* reúne en pestañas lo que se hace con OBS, y se abre desde
el menú *OBS*. Si OBS está cerrado, el panel lo abre. Todo se puede seguir
haciendo en OBS, y el complemento de OBS para NVDA sigue funcionando.

### General

*Estado* resume la transmisión, la grabación, la escena actual, el
micrófono y el uso del equipo. *Mostrar OBS* trae al frente la ventana de
OBS, también desde el área de notificación. Si OBS tarda en conectar o deja
de responder un momento, avisa y sigue cuidando el directo en vez de
abandonarlo, con el sonido de desconexión y el de reconexión cuando vuelve.
El panel sigue respondiendo mientras espera a OBS y se puede cerrar en
cualquier momento. Con el directo en el aire, los avisos de problemas no
abren un cuadro encima del juego. *Cerrar OBS*, también en el menú *OBS*, cierra OBS sin
forzarlo, así no pregunta por el modo seguro al volver a abrirlo. Si OBS
está transmitiendo o grabando, no lo cierra y avisa.

*Probar equipo…* graba unos segundos con el perfil en uso para ver si la
PC pierde fotogramas. Si los pierde, prueba ajustes más livianos hasta dar
con unos que funcionan y ofrece guardarlos en el perfil. Con el plugin
Vertical Canvas de Aitum en OBS, el cuadro ofrece incluir el lienzo
vertical, para saber si la PC puede transmitir en las dos orientaciones a
la vez. Las grabaciones de la prueba se borran al terminar.

*Probar conexión…* hace un directo privado de prueba en YouTube, que
nadie ve y que se borra solo, para saber qué tasa de bits admite tu
conexión, y ofrece guardarla en el perfil. Necesita la sesión de Google.

Las pruebas del equipo y de la conexión muestran su avance en una ventana,
con un sonido de espera, y si fallan dejan el error escrito en ella. El
resultado se cierra con `Esc`. En la
prueba de la conexión, si un intento falla por un error de OBS, Guyrapu
vuelve a intentarlo y sigue con el siguiente. Si la sesión de YouTube
caducó, lo dice y explica cómo volver a iniciarla.

### Escena

La lista *Escenas* muestra cada escena, si es la actual y cuántas fuentes
tiene. Recorrerla no cambia lo que se emite: *Cambiar escena* pone al aire
la escena elegida, y *Agregar escena…* crea una nueva. Suena al llegar a la
orilla y el doble clic cambia de escena.

*Crear versión vertical*, en el menú contextual de una escena, crea una
copia con el mismo nombre seguido de «vertical», con las mismas fuentes y
un diseño vertical. Al transmitir en vertical, esa copia sale al aire, y al
terminar vuelve la escena que había.

La lista *Fuentes* muestra las fuentes de la escena elegida. Cada fila dice
primero si la fuente tiene un problema (oculta, tapada o fuera del vídeo),
después dónde está, con las mismas palabras que el cuadro de tamaño y
posición, y qué parte del vídeo ocupa. Si una fuente no entra, sugiere
*Aplicar diseño* para ajustarla. El menú
contextual de cada fila reúne sus acciones. *Tamaño y posición…* la coloca
en una de nueve posiciones, con un tamaño de un quinto a todo el ancho del
vídeo, y *Mover con flechas* la mueve en pasos. Si la escena no tiene
fuentes, la lista lo dice y explica cómo agregar una.

*Agregar fuente…* agrega a la escena una cámara, una captura de ventana, de
juego o de pantalla, una imagen, un archivo multimedia, un texto, el chat en
el vídeo o una fuente de otra escena.

*Aplicar diseño…* reparte toda la escena de una vez. Trae tres diseños de
fábrica, *Pantalla completa*, *Imagen en imagen* y *Dividida en dos*, y en el
cuadro se elige qué fuente va en cada lugar, la esquina, el reparto y el
chat. *Ajuste*
decide qué pasa si la proporción no coincide: *Ajustar* muestra la fuente
entera, *Cubrir* recorta los bordes y *Automático* llena con la cámara y
ajusta lo demás. *Guardar como…* guarda un diseño propio. En el menú de
transformar una fuente, *Ajustar al vídeo* la agranda para llenar el vídeo,
como en OBS. En un lienzo
vertical, *Dividida en dos* apila las fuentes arriba y abajo, y el chat en
franja va abajo.

*Deshacer todos los cambios* devuelve la escena a como estaba al abrir el
panel.

| Tecla en la lista Escenas | Acción |
|---|---|
| `Intro` | Cambiar a esa escena |
| `F2` | Cambiar nombre |
| `Ctrl+D` | Duplicar |
| `Supr` | Eliminar |

| Tecla en la lista Fuentes | Acción |
|---|---|
| `Espacio` | Mostrar u ocultar la fuente |
| `Alt+Intro` | Propiedades |
| `F2` | Cambiar nombre |
| `Ctrl+D` | Duplicar |
| `Supr` | Eliminar |
| `Ctrl+Inicio` / `Ctrl+Fin` | Traer al frente o enviar al fondo |
| `Ctrl+Flecha arriba` / `abajo` | Traer adelante o enviar atrás |
| `Ctrl+Z` | Deshacer |

| Tecla en Mover con flechas | Acción |
|---|---|
| Flechas | Mover 10 píxeles |
| `Ctrl` y flechas | Mover 50 píxeles |
| `Mayús` y flechas | Mover 1 píxel |
| `Intro` | Confirmar |
| `Esc` | Deshacer el movimiento |

### Perfiles de OBS

La lista *Perfiles de OBS* muestra cada perfil de OBS, su orientación y
para qué se usa: transmitir en horizontal, transmitir en vertical o grabar.

- *Usar este perfil* pasa OBS a ese perfil.
- *Usar para…* elige para qué se usa. Lo mismo se elige en *Preferencias*,
  categoría *OBS*, donde *El perfil que tenga OBS* deja OBS como está.
- *Nuevo…*, *Duplicar…* y *Eliminar perfil* crean, copian y eliminan
  perfiles.
- *Editar ajustes…* cambia el lienzo, la salida, los fotogramas por
  segundo, el codificador, la transmisión, la grabación, el búfer de clips
  y el audio, incluido el dispositivo de escucha del monitoreo.
- *Preparar perfiles…* crea un perfil para transmitir en horizontal, otro
  en vertical y otro para grabar, comprueba qué ajustes funcionan bien en
  tu PC, los deja asignados y dice qué hizo. Los perfiles que ya tenías no
  cambian. Muestra su avance en una ventana, con un sonido de espera, y si
  falla deja el error escrito en ella. El resumen se cierra con `Esc`.

Al transmitir o grabar sin directo, Guyrapu pasa OBS al perfil asignado, y
al terminar vuelve al que tenía. Editar los ajustes de un perfil que no está
en uso no cambia el perfil de OBS. Al cambiar de perfil, Guyrapu iguala antes
el audio del perfil de destino con el del perfil en uso, para que OBS no pida
reiniciar.

Sin perfiles, la lista dice cómo crear uno. *Nuevo…* crea el perfil y abre
sus ajustes. En la lista, `Supr` elimina el perfil, `Intro` abre sus
ajustes y la tecla Aplicaciones abre un menú con las mismas acciones que
los botones.

### Transmisión

*Transmitir en directo* abre el cuadro *Transmitir a*, igual que el botón de
la ventana principal, y *Restream…* abre la ventana de Restream. Durante el
directo, *Finalizar directo* lo termina igual que ese botón, incluso el
directo de YouTube.

### Audio

La lista *Fuentes de audio* muestra cada fuente con su estado y sus
filtros. Si no hay fuentes de audio, la lista lo dice. Los botones actúan
sobre la fuente elegida:

- *Silenciar* la silencia o la activa.
- *Probar nivel* dice cada cinco segundos si el nivel es correcto, bajo o
  alto, o si se satura, hasta pulsar *Detener prueba*.
- *Filtros…* activa la eliminación de ruido, la puerta anti-ruidos y la
  ganancia. Si OBS ya tenía uno de esos filtros, se usa ese.
- *Escuchar* deja oír la fuente con sus filtros por el dispositivo de
  monitorización de OBS. Usa auriculares para evitar el acople.
- *Elegir micrófono…* fija el dispositivo del micrófono.

### Grabación

*Iniciar grabación* y *Detener grabación* graban sin transmitir, y *Pausar
grabación* pausa la grabación en curso: si no hay ninguna, avisa lo mismo
que el comando del menú. La lista *Grabaciones y clips* reúne lo grabado y
los clips, del más nuevo al más antiguo. Suena al llegar a la orilla, busca
al teclear y el doble clic abre la grabación. El menú contextual abre el
archivo o su carpeta, copia la ruta o lo elimina de la lista sin borrar el
archivo, y muestra la tecla de cada acción. Si OBS convierte la grabación a
MP4 al terminar, la lista muestra el MP4.

## <a id="restream"></a>Restream

Restream envía una sola transmisión a varias plataformas a la vez. La
ventana de Restream se abre con *Restream…*, en el menú *Transmisión*, y
tiene cuatro pestañas.

### Cuenta

Muestra la cuenta conectada y sus destinos, y permite conectarla, volver a
autorizarla o desconectarla.

### Destinos

Lista los canales de la cuenta con su plataforma, y los desactivados lo
dicen al final. *Agregar destino…* abre la página de Restream en el
navegador o agrega un destino manual con servidor y clave. El menú
contextual de cada destino lo activa o lo desactiva, copia su enlace, lo
abre en el navegador, le cambia el título o el nombre, y lo elimina. Sin
cuenta conectada, la lista dice cómo conectarla; sin destinos, dice cómo
agregar uno.

### Perfiles

Un perfil guarda a qué destinos se transmite y con qué orientación, y
aparece con su nombre en el cuadro *Transmitir a*. La lista tiene un botón
por acción: *Nuevo perfil…*, *Editar…*, *Cambiar nombre…*, *Duplicar* y
*Eliminar*. Sin perfiles, dice cómo crear uno. En el perfil:

- *Orientación* es *Horizontal*, *Vertical* u *Horizontal y vertical a la
  vez*.
- *YouTube, el canal de tu sesión de Google* suma ese canal, con el
  directo que Guyrapu crea a partir de los datos que escribes al
  transmitir.
- *Chat que lee Guyrapu* elige qué chat se lee si el perfil tiene YouTube
  y TikTok. Con *YouTube y TikTok*, que viene elegida en los perfiles
  nuevos, se leen los dos.

### Horizontal y vertical a la vez

Con la orientación *Horizontal y vertical a la vez*, el horizontal va
directo a YouTube y el vertical a los demás destinos del perfil, como
TikTok. El perfil tiene que incluir YouTube, y los canales de YouTube de
la cuenta de Restream se desactivan durante el directo, para que YouTube
no reciba también el vertical.

Hace falta el plugin Vertical Canvas de Aitum en OBS. Se descarga de
github.com/Aitum/obs-vertical-canvas/releases y se instala con OBS
cerrado. La primera vez, Guyrapu agrega al plugin la salida «Guyrapu»: si
OBS está abierto, lo dice, lo cierra y lo vuelve a abrir.

Antes de salir al aire, Guyrapu copia al lienzo vertical las versiones
verticales de tus escenas, las que crea *Crear versión vertical*.
Durante el directo, cuando cambias de escena, el vertical pasa a la
versión vertical de esa escena, y si no la tiene, lo dice una vez. Si el
vertical se interrumpe, suena un aviso y el horizontal sigue: Guyrapu lo vuelve
a intentar cada 30 segundos y avisa cuando vuelve. *Finalizar directo*
detiene los dos.

### Eventos

*Mostrar* elige entre los eventos próximos, los que están en directo y el
historial. *Detalle del evento* muestra su estado, sus horarios, sus
destinos y la descripción. El menú contextual copia los enlaces o la
información del evento, ofrece *Abrir directo* y agrega las estadísticas al
detalle. Si no hay eventos para el filtro elegido, la lista lo dice.

### Avisos durante el directo

Con un perfil de Restream, Guyrapu avisa con un sonido propio cuando
Restream deja de recibir la señal de OBS y cuando la recupera, cuando la
señal es débil y cuando un destino se desconecta o vuelve.

## Encuadre de cámara

Si la escena actual tiene una cámara, Guyrapu dice cómo te ve: cuántos
rostros hay, si estás centrado, lejos, de lado o fuera del borde, si falta
luz o hay contraluz, y si la imagen se congeló. Izquierda y derecha se
dicen como el movimiento que tienes que hacer: «Muévete a tu izquierda.».
La imagen se analiza en el equipo y no se envía a ningún sitio.

Los comandos están en el menú *OBS*:

- *Anunciar encuadre de cámara* dice el encuadre. Dos veces seguidas,
  inicia la guía con pitidos, que suenan del lado hacia el que tienes que
  moverte, más agudos para subir y más graves para bajar. En el centro
  suena una confirmación.
- *Avisar si el rostro queda fuera del encuadre* avisa con un sonido cuando el
  rostro sale y con otro cuando vuelve.
- *Mostrar u ocultar la cámara* oculta la cámara de la escena sin
  desactivar el dispositivo.

En *Preferencias*, categoría *Cámara*, se elige la cámara de OBS, el sonido
de la guía y si se invierten izquierda y derecha.

## Interacción

La ventana *Interacción* reúne lo que el público ve y oye en el directo. Se
abre con *Abrir Interacción…*, en el menú *Interacción*, o con
`Ctrl+Mayús+A`, y vuelve a abrirse en la última página usada. Tiene una
lista de páginas a la izquierda y, a la derecha, la lista y las acciones de
la página elegida.

Las páginas se reparten por cuándo sale algo. *Comandos* contiene lo que
escribe el público, *Alertas* lo que pasa en el directo y *Mensajes
automáticos* lo que sale solo cada tanto. Después vienen *Encuestas*,
*Preguntas* y *Metas*, y al final *Medios*, *Estilos* y *Palabras
bloqueadas*. Para abrir la ayuda de la página que tienes delante, pulsa
`F1` o el botón *Ayuda*. Las listas vacías dicen qué aparece en ellas y
cómo agregar el primer elemento.

### <a id="contenido"></a>Contenido

Los cuadros de comandos, alertas y mensajes automáticos comparten la
sección *Contenido*. Tiene cinco campos en este orden: *Texto*, *Mostrar
en*, *Medio*, *Segundos en pantalla* y *Estilo*. En *Texto* escribes lo que
sale y puedes usar variables. *Mostrar en* elige *Vídeo*, *Chat* o *Chat y
vídeo*. *Medio* elige un archivo de la carpeta Medios o *Ninguno*.
*Segundos en pantalla* fija cuánto queda en el vídeo, y *Estilo* elige su
aspecto. Para guardar hace falta un texto o un medio. Si solo va al chat,
hace falta el texto y no puede superar los 200 caracteres.

### <a id="comandos"></a>Comandos

Los comandos son lo que escribe el público en el chat. Para crear
`!hola`, ve a *Comandos*, llega a *Agregar* con `Tab` y pulsa `Intro`. En
*Palabra* escribe `!hola`, en *Texto* escribe `Hola, gracias por estar
aquí` y en *Mostrar en* elige *Chat y vídeo*. Pulsa *Aceptar* y Guyrapu
anuncia «Comando agregado». Cuando alguien escriba `!hola`, el público ve
la tarjeta en el vídeo y el texto en el chat, y la voz lee el mensaje del
chat. `F2` dice cuántos comandos respondió Guyrapu y cuál fue el último.

Un comando también puede salir solo como sonido. Crea `!aplausos` con
*Palabra* `!aplausos`, deja *Texto* vacío y elige `aplauso.wav` en *Medio*.
En *Mostrar en* deja *Vídeo*. El público oye el sonido en el vídeo y no ve
ninguna tarjeta. Copia el archivo en la carpeta Medios antes de abrir el
cuadro para que aparezca en la lista.

En *Ubicación* eliges *Al principio del mensaje* o *En cualquier parte del
mensaje*. En *Alias* escribes otras palabras separadas por comas, como
`hola, saludo`, que responden igual. En *Permiso* eliges *Todos*, *Solo
moderadores*, *Una lista de nombres* o *Solo con el atajo*. Las esperas
*Espera entre usos (segundos):* y *Espera por persona (segundos):* limitan
las respuestas. En *Atajo* eliges *Ninguno* o `Ctrl+Alt+Mayús` más un número
del 1 al 9, y el comando responde desde cualquier aplicación. Con *Solo con
el atajo*, el comando no responde al chat y solo responde a esa tecla. Lo
que estaba en «Disparadores» como comando, palabra o atajo pasó solo a esta
página.

*Pausar comandos*, en el menú *Interacción*, o `Ctrl+Alt+Mayús+C` desde
cualquier aplicación, deja de contestar todos a la vez. La lista de comandos
que pide el público se edita como uno más: su palabra, de fábrica
`!commands`, y `!comandos` en español y portugués, su texto, dónde sale y
su estilo, y cada comando elige si aparece en ella.

### <a id="alertas"></a>Alertas

Las alertas responden a lo que pasa en el directo: un Super Chat, una
membresía, un seguidor o un regalo de TikTok. Antes se llamaban
«Disparadores». Para crear una alerta de Super Chat, ve a
*Alertas* y pulsa *Agregar*. En *Nombre* escribe `Gracias por el Super
Chat`, en *Evento* elige *Super Chats y regalos* y en *Cantidad mínima*
escribe `5`. En *Texto* escribe `Gracias, {usuario}, por {cantidad}.`, en
*Medio* elige una imagen de la carpeta Medios y en *Mostrar en* elige *Chat
y vídeo*. Pulsa *Aceptar*.

Cuando llegue un Super Chat de 5 o más, el público ve la imagen y la
tarjeta en el vídeo y el texto en el chat. Guyrapu escribe la tarjeta en el
chat y la voz lee el Super Chat. En *Probar sin directo*, la lista
*Resultados* dice «Respondió la alerta Gracias por el Super Chat». En
*Permiso y espera* eliges quién puede activarla y cada cuánto tiempo, y en
la tarjeta puedes usar `{usuario}`, `{cantidad}`, `{regalo}`, `{texto}` y
`{contador}`. La parte de los antiguos disparadores que respondía a
comandos, palabras o atajos está ahora en *Comandos*. La casilla *Avisar
cuando se muestra en el vídeo* hace que la voz diga, por ejemplo, «Alerta
Gracias por el Super Chat en el vídeo, de Ana.». Viene desmarcada.

### <a id="mensajes-automaticos"></a>Mensajes automáticos

Los mensajes automáticos salen solos cada cierto tiempo, por ejemplo tus
redes cada diez minutos. Para crear uno con imagen, ve a *Mensajes
automáticos*, pulsa *Agregar* y en *Nombre* escribe `Redes`. En *Texto*
escribe `Sígueme en @tucanal`, en *Medio* elige `redes.png` y en *Mostrar
en* elige *Chat y vídeo*. En *Intervalo mínimo, en minutos* deja `10` y
pulsa *Aceptar*. Con la sesión de Google iniciada y un directo de YouTube
conectado, el público ve la imagen y el texto en el vídeo y el texto en el
chat, y la voz lee el mensaje. `F2` dice qué hay en el vídeo.

También puedes duplicarlos, ordenarlos, escucharlos, exportarlos e
importarlos. Los que eligen el vídeo entran animados en OBS, quedan sus
segundos y salen uno por vez, y respetan *Mensajes del chat entre uno y
otro*. YouTube suele bloquear los enlaces: escribe el nombre de usuario en
su lugar. Si YouTube devuelve un error, los mensajes se detienen y Guyrapu
lo avisa una vez. `Supr` o el menú contextual eliminan el mensaje elegido.

### <a id="encuestas"></a>Encuestas

En *Encuestas* preparas la pregunta, las opciones, la duración y dónde sale
el resultado. Por ejemplo, escribe `¿Qué juego sigue?`, agrega `Uno` y
`Dos`, pon `2` en la duración y elige *Vídeo*. Inicia la encuesta desde
Interacción. El público ve la pregunta en el vídeo con los votos y el
tiempo, y vota escribiendo `!1` o `!2` desde cualquier chat. Con
`Ctrl+Alt+Mayús+I` oyes la encuesta con sus votos, y `Ctrl+Alt+Mayús+E` la
cierra antes de tiempo. Sin pulsar ninguna tecla, la voz dice «Quedan 10
segundos de la encuesta» y, por ejemplo, «Va ganando Uno, con 3 votos» cuando
cambia la opción que va ganando. La casilla *Avisar cuando quedan 10 segundos
y cuando cambia quién gana* calla estos avisos. Viene marcada.

### <a id="preguntas"></a>Preguntas

El público deja preguntas escribiendo `!pregunta` o `!q` en el chat. Por
ejemplo, escribe `!pregunta ¿Cómo se llama tu canal?` y la pregunta entra en
la cola, una por persona. La página *Preguntas* muestra la cola al día.
Selecciona la pregunta y pulsa *Mostrar en el vídeo*: el público la ve en la
tarjeta. Con `Ctrl+Alt+Mayús+R` oyes la más antigua desde cualquier aplicación.
También puedes marcarla como respondida, eliminarla o vaciar la cola. Cada
pregunta tiene su estilo propio.

### <a id="metas"></a>Metas

En *Metas* preparas las metas del directo: qué cuentan, cuánto hace falta y
con qué estilo y festejo se muestran. Cuentan me gusta, seguidores,
miembros, regalos o Super Chats. Por ejemplo, crea una meta de seguidores con
objetivo `50`. Al cumplirse, suena un aviso y el público ve una tarjeta en el
vídeo con el festejo. Puedes mostrar el avance fijo, por ejemplo
«Seguidores: 12 de 50», y se pone al día mientras llegan. Durante el directo,
la voz dice «Meta Seguidores: a la mitad, 25 de 50» y, al llegar al 90 por
ciento, «Meta Seguidores: cerca del objetivo, 45 de 50». La casilla *Avisar a
la mitad y cerca del objetivo* calla estos avisos. Viene marcada. Las metas de
me gusta de TikTok siguen el número que muestra TikTok, con los me gusta que
llegaron antes de conectar el chat.

### <a id="medios"></a>Medios

La carpeta *Medios* está junto a la aplicación, como la carpeta Música. El
botón *Abrir carpeta* de esta página la abre en el Explorador. Copia ahí un
archivo de imagen (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`), de vídeo
(`.mp4`, `.webm`, `.mov`, `.mkv`) o de sonido (`.wav`, `.mp3`, `.ogg`,
`.m4a`) y aparece en la lista al volver a la página. Por ejemplo, copia
`aplauso.wav` y pulsa *Escuchar*: oyes el nombre y la descripción del medio y
se reproduce el sonido o el vídeo. Pulsa *Escuchar* otra vez o `Esc` para
detenerlo.
El público lo oye o lo ve cuando un comando o una alerta lo muestra en el
vídeo. Los medios de versiones anteriores se mudan solos a esta carpeta la
primera vez que abres la aplicación.

*Describir imagen* pide a la inteligencia artificial una frase sobre lo que
muestra la imagen o el GIF, para que `F2` y la lista digan qué ve el
público. Los sonidos y vídeos se igualan de volumen al agregarlos. El
deslizador *Volumen de los medios en el vídeo* los equilibra con la voz y el
juego. Cada medio de sonido o vídeo tiene además su *Volumen* en *Agregar
medio* o *Editar medio*, de 0 a 200, que se suma a la igualación y al volumen
general. *Escuchar* lo reproduce con esa misma ganancia, igual que en el
directo. Al elegir un medio y pulsar *Crear comando*, se abre el cuadro de
comando con ese medio y un nombre sugerido. Al aceptar, Guyrapu dice «Comando
agregado» y el comando queda en *Comandos*. También puedes agregar, editar,
duplicar, exportar e importar medios; *Eliminar* quita también el archivo de
la carpeta.

### <a id="estilos"></a>Estilos

En *Estilos* creas, duplicas, exportas e importas estilos para los mensajes
del vídeo, con fuente, colores por nombre, fondo, zona y animación. Por
ejemplo, crea un estilo con fuente grande y fondo azul, y pulsa *Establecer
como predeterminado…* para usarlo en los comandos. Cada estilo puede ser el
predeterminado de los mensajes automáticos, los comandos, las alertas, las
encuestas o las metas, y cada elemento puede usar el de su tipo. *Probar*,
en esta página y en *Mensajes automáticos*, arma la tarjeta fuera del aire
y dice dónde sale, cuánto ocupa y si tiene algún problema de fuente o de
contraste.

### <a id="palabras-bloqueadas"></a>Palabras bloqueadas

En *Palabras bloqueadas* escribes las palabras que se tapan en el nombre y
el texto del público que muestran las respuestas de los comandos. Por
ejemplo, agrega `spam`: si alguien escribe `!hola spam`, la tarjeta del
comando muestra `***` en lugar de la palabra. Un texto hecho casi todo de
símbolos no se muestra.

### <a id="probar-sin-directo"></a>Probar sin directo

*Probar sin directo…*, en el menú *Interacción*, y el botón *Probar sin
directo* de la ventana ensayan la interacción sin salir al aire. No se puede
abrir con un directo conectado. En *Plataforma* eliges YouTube o TikTok. El
*Tipo* cambia con la plataforma: en YouTube tienes *Mensaje*, *Super Chat* y
*Membresía*; en TikTok, *Mensaje*, *Regalo*, *Seguidor nuevo*, *Me gusta* y
*Directo compartido*. En YouTube aparece además *Rol*, con *Público*,
*Moderador* y *Propietario del canal*. Escribes el autor y lo que pida el
tipo, por ejemplo cantidad y mensaje para un Super Chat, y pulsas *Enviar*.

La lista *Resultados* guarda una línea por envío con la hora, lo que
enviaste y lo que respondió. Por ejemplo: «Respondió el comando !hola.»,
«Respondió la alerta Gracias por el Super Chat.», «Voto contado en la
encuesta», «Pregunta agregada a la página Preguntas.» o «La meta avanzó a 12
de 50.». Si nada responde, el motivo dice por qué:

- «ningún comando ni alerta usa ese mensaje» o «ninguna alerta usa ese
  evento», cuando no hay nada que coincida.
- «el comando … está en espera, faltan … segundos», cuando su espera aún no
  terminó. Lo mismo se dice de una alerta.
- «el comando … es solo para …», cuando el permiso no incluye al autor, y
  «el comando … está en pausa» o «los comandos están en pausa», cuando
  están detenidos.

Lo que va al vídeo se ve en OBS como en un directo, sin publicar nada en los
chats y sin que la voz lo lea. Al cerrar la ventana termina el ensayo y se
descarta lo que dejó.

### Atajos globales

Los atajos globales `Ctrl+Alt+Mayús` de la interacción funcionan aunque el
foco esté en otro programa: pausan, omiten y vacían lo que sale en el vídeo,
silencian los medios, activan el modo pánico, activan o desactivan los mensajes
automáticos, pausan los comandos, cierran la encuesta, leen la siguiente
pregunta y dicen el estado de la interacción. Están en la tabla
[Atajos de teclado](#atajos-de-teclado), en la familia *Interacción en
directo*.

## <a id="descargas"></a>Descargas e historial

El *Administrador de descargas* descarga vídeos, audio o listas de YouTube
en MP4, WebM, MP3 o M4A, dos a la vez. Lo descargado queda en la carpeta
Descargas, junto a la aplicación. En la pestaña *Buscar en YouTube*,
Espacio reproduce un resultado en la música sin descargarlo. *Mostrar más*
se alcanza siempre con `Tab` y dice cuando no hay más resultados. NVDA dice
el nombre de la lista de resultados y de la lista de descargas. Si una
descarga deja de avanzar durante dos minutos, Guyrapu la corta y avisa con
un error, y *Reintentar* la retoma: si se perdió la conexión, el error lo
dice en vez de mostrar un código. Las acciones que no sirven para la
descarga elegida siguen en el menú y dicen por qué. Si las descargas fallan,
usa *Actualizar yt-dlp…*, en el menú *Herramientas*.

El *Historial de directos* muestra lo que viste, con una pestaña para
YouTube y otra para TikTok. Cada lista tiene menú contextual, y una pestaña
vacía dice que no hay entradas de esa plataforma.

## Estado por voz

*Anunciar estado*, en el menú *Ver*, resume la conexión, el directo, los
espectadores, los mensajes leídos y las donaciones, con frases cortas y
uniformes. Cuando transmites a YouTube y TikTok a la vez, los espectadores
son los de las dos plataformas. Qué se incluye se elige en *Preferencias*,
categoría *Estado (F2)*. Dos veces seguidas, abre la ventana *Estado de la
sesión*, con cada dato en una línea. `Ctrl+Alt+Mayús+I` dice cómo va la
interacción del directo: la encuesta con sus votos, la batalla, la meta, lo
que sale en el vídeo y cuántas preguntas esperan. Si no hay nada, lo dice.

## <a id="ia"></a>Preguntar a la IA

Una inteligencia artificial mira una captura de OBS y dice qué se ve, por
ejemplo si una fuente sale en negro. Requiere OBS abierto y la clave de un proveedor.

En *Preferencias*, categoría *Inteligencia artificial*, se elige el
proveedor, como Google Gemini, OpenAI, Anthropic u OpenRouter, se guarda la
clave y se elige el modelo. Al actualizar la lista de modelos, Guyrapu prueba
el modelo elegido con tu clave y avisa si no responde o si es de pago. La
clave queda en el Administrador de credenciales de Windows. Si la clave no tiene el formato que Guyrapu
espera, avisa y ofrece usarla de todos modos, por si el proveedor cambió el
formato.

*Preguntar a la IA sobre la imagen…*, en el menú *Ver*, abre una ventana
donde *Agregar captura* elige la escena o una fuente, y también el fotograma
del vídeo que muestra el reproductor, con OBS abierto o cerrado. La pregunta
se escribe en *Mensaje*. *Consulta rápida a la IA* envía la escena actual y
lee la respuesta sin abrir ninguna ventana. `Ctrl+F2` y `Ctrl+Mayús+F2`
dicen la escena y sus avisos con frases cortas y uniformes, y la consulta
rápida avisa si se cancela. Con OBS cerrado, `Ctrl+Mayús+F2` describe el
fotograma que se ve en el reproductor; en modo solo audio no hay imagen y lo
dice.

La conversación tiene menú contextual, `Ctrl+C` copia el mensaje elegido y
suena la orilla al llegar al principio o al final. `Ctrl+S`, o *Guardar
conversación…* en el menú de la lista *Conversación*, guarda la conversación
entera en un archivo de texto. La IA cita tal como está escrito el texto que
se lee en la imagen, como un cartel, una alerta o el chat dentro del vídeo.
Con los modelos que lo permiten, las respuestas salen más parejas entre una
consulta y la siguiente.

La captura y lo que escribas se envían al proveedor, y el primer envío pide
confirmación. Una captura en negro, como la que deja la cortina de pantalla
de NVDA, no se envía. En ese caso, cambia en OBS el método de captura de esa
fuente a Windows 10.

## Sesión de Google

La sesión de Google permite moderar, escribir en el chat, comentar vídeos y
crear el directo de YouTube. Sin ella, todo lo demás funciona.

Para iniciarla, abre *Preferencias*, categoría *YouTube*, pulsa *Iniciar
sesión* y autoriza en el navegador. Las sesiones de YouTube y de Restream
se guardan cifradas con tu cuenta de Windows: si copias la carpeta de la
aplicación a otro equipo, tendrás que volver a iniciarlas. La cuota diaria
de YouTube se comparte entre quienes usan Guyrapu. La cuota estimada se
mantiene al día sola con los costos que publica Google, una vez por semana.
Para tener una propia, consulta la [guía de configuración de la
API](../CONFIGURACION_API.md).

## <a id="preferencias"></a>Preferencias

*Preferencias…*, en el menú *Herramientas*, reúne la configuración por
categorías, y los cambios se aplican al pulsar *Guardar*. En *General* se
elige el idioma y el canal de actualización, y se exportan, se importan o
se restablecen las preferencias. *Mostrar avisos importantes también en un
cuadro de mensaje* muestra además en un cuadro el resultado de lo que haces.
Cada categoría se prepara la primera vez que la eliges, así la ventana abre
más rápido.

Las preferencias se guardan en `config.ini` y `sounds.ini`, en la carpeta
`data` junto a la aplicación.

### Cambiar un atajo

En la categoría *Atajos*, cada acción tiene un botón con su atajo. Pulsa el
botón y después la combinación nueva. Si la combinación ya está en uso o no
corresponde a esa familia, Guyrapu dice por qué y sigue esperando. Los atajos
fijos se alcanzan con `Tab`: se oye su combinación y, al activarlos, que no
se pueden cambiar. *Restablecer atajos de fábrica* vuelve a los atajos
originales.

| Tecla al cambiar un atajo | Acción |
|---|---|
| `Intro` | Dejar la acción sin atajo |
| `Esc` | Cancelar |

## Atajos de teclado

Cada familia de atajos usa sus propias teclas modificadoras. Todos figuran
también en la barra de menús, junto a su comando. En las listas con
acciones, escribir las primeras letras salta al elemento que empieza así, al
llegar al principio o al final suena un aviso y el menú contextual muestra la
tecla de cada acción. `Mayús+F10` abre ese menú en las listas que lo tienen.

### Fijos

| Atajo | Acción |
|---|---|
| `F1` | Abrir el manual en la sección de la ventana |
| `F6` / `Mayús+F6` | Región siguiente o anterior |
| `Ctrl+Tab` | Cambiar de pestaña |
| `Alt+F4` | Salir |

### Reproductor (Ctrl)

| Atajo | Acción |
|---|---|
| `Ctrl+P` | Reproducir o pausar |
| `Ctrl+Flecha izquierda` / `derecha` | Retroceder o avanzar 1 minuto |
| `Ctrl+Flecha arriba` / `abajo` | Subir o bajar el volumen del reproductor |
| `Ctrl+Fin` | Ir al directo |
| `Ctrl+D` | Detener la reproducción |
| `Ctrl+M` | Silenciar o activar el audio |
| `Ctrl+F` | Pantalla completa |

### Chat (Alt)

| Atajo | Acción |
|---|---|
| `Alt+Intro` | Ir al cuadro de escritura |
| `Alt+B` | Buscar en el chat |
| `Alt+P` | Participación en el chat |

### Ventanas (Ctrl+Mayús)

| Atajo | Acción |
|---|---|
| `Ctrl+Mayús+P` | Preferencias |
| `Ctrl+Mayús+A` | Mensajes automáticos |
| `Ctrl+Mayús+H` | Historial de directos |
| `Ctrl+Mayús+R` | Restream |
| `Ctrl+Mayús+D` | Administrador de descargas |
| `Ctrl+Mayús+M` | Música |
| `Ctrl+Mayús+I` | Preguntar a la IA sobre la imagen |
| `Ctrl+Mayús+O` | Panel de OBS |

### Directo y OBS (Alt+Mayús)

| Atajo | Acción |
|---|---|
| `Alt+Mayús+C` | Conectar |
| `Alt+Mayús+D` | Desconectar |
| `Alt+Mayús+L` | Ir a la lista del panel actual |
| `Alt+Mayús+E` | Copiar el enlace del directo |
| `Alt+Mayús+I` | Marcar incidencia |
| `Alt+Mayús+M` | Silenciar el micrófono de OBS |
| `Alt+Mayús+G` | Iniciar o detener la grabación |
| `Alt+Mayús+P` | Pausar o reanudar la grabación |
| `Alt+Mayús+R` | Guardar un clip |
| `Alt+Mayús+A` | Avisar si OBS se sobrecarga |
| `Alt+Mayús+O` | Mostrar OBS |

### Voz y lectura (teclas F)

| Atajo | Acción |
|---|---|
| `F2` | Anunciar el estado. Dos veces, abrir la lista |
| `F3` | Anunciar el autor del último mensaje |
| `F4` | Silenciar la lectura |
| `F5` | Pausar o reanudar la lectura |
| `F7` | Silenciar los sonidos |
| `F8` | Detener la voz actual |
| `F9` / `F10` | Bajar o subir la velocidad de la voz |
| `F11` / `F12` | Bajar o subir el volumen de la voz |
| `Ctrl+F9` / `Ctrl+F10` | Bajar o subir el tono de la voz |
| `Ctrl+F2` | Describir la escena de OBS |
| `Ctrl+Mayús+F2` | Consulta rápida a la IA |
| `Ctrl+F3` | Anunciar el encuadre de cámara. Dos veces, guía con pitidos |
| `Ctrl+Mayús+F3` | Avisar si el rostro queda fuera del encuadre |
| `Alt+F3` | Mostrar u ocultar la cámara |

### Interacción en directo (Ctrl+Alt+Mayús)

| Atajo | Acción |
|---|---|
| `Ctrl+Alt+Mayús+P` | Pausar o reanudar la cola del vídeo |
| `Ctrl+Alt+Mayús+S` | Omitir el mensaje del vídeo |
| `Ctrl+Alt+Mayús+V` | Vaciar la cola del vídeo |
| `Ctrl+Alt+Mayús+M` | Silenciar o activar los medios |
| `Ctrl+Alt+Mayús+Q` | Activar o desactivar el modo pánico |
| `Ctrl+Alt+Mayús+A` | Activar o desactivar los mensajes automáticos |
| `Ctrl+Alt+Mayús+C` | Pausar o reanudar todos los comandos del chat |
| `Ctrl+Alt+Mayús+E` | Cerrar la encuesta |
| `Ctrl+Alt+Mayús+R` | Leer la siguiente pregunta |
| `Ctrl+Alt+Mayús+I` | Estado de la interacción |

El ensayo *Probar sin directo…* y los atajos globales se explican en
[Interacción](#interacción).

### Música (Ctrl+Alt)

| Atajo | Acción |
|---|---|
| `Ctrl+Alt+Espacio` | Reproducir o pausar |
| `Ctrl+Alt+Flecha derecha` / `izquierda` | Canción siguiente o anterior |
| `Ctrl+Alt+Flecha arriba` / `abajo` | Subir o bajar el volumen |
| `Ctrl+Alt+Mayús+Flecha derecha` / `izquierda` | Avanzar o retroceder 10 segundos |
| `Ctrl+Alt+T` | Anunciar la canción actual |
| `Ctrl+Alt+M` | Silenciar o activar |
| `Ctrl+Alt+D` | Detener |
| `Ctrl+Alt+A` | Orden aleatorio |
| `Ctrl+Alt+R` | Cambiar la repetición |

### Filtro y mensajes recientes del chat (Ctrl+Mayús)

| Atajo | Acción |
|---|---|
| `Ctrl+Mayús+'` | Filtro anterior del chat |
| `Ctrl+Mayús+¿` | Filtro siguiente del chat |
| `Ctrl+Mayús+1` | Leer el último mensaje |
| `Ctrl+Mayús+2` a `Ctrl+Mayús+9` | Leer del segundo al noveno desde el final |
| `Ctrl+Mayús+0` | Leer el décimo desde el final |

Los dos atajos del filtro usan las teclas a la derecha del cero y recorren
la lista del chat en el orden del menú, con vuelta en los extremos. En el
teclado de España son `Ctrl+Mayús+'` y `Ctrl+Mayús+¡`; en el de Estados
Unidos, `Ctrl+Mayús+-` y `Ctrl+Mayús+=`.

Con *Usar atajos del chat en cualquier aplicación*, en *Preferencias*,
categoría *Lectura*, todos estos atajos funcionan también con otra
aplicación en primer plano. Si otra aplicación ya usa una de estas
combinaciones, suena un tono y Guyrapu dice cuál.

## Actualizar

*Buscar actualizaciones…*, en el menú *Ayuda*, dice si hay una versión
nueva, muestra sus novedades y la instala. Guyrapu se cierra y vuelve a
abrirse en alrededor de un minuto, y conserva la carpeta `data`, las
descargas y los sonidos propios. Si la versión nueva no abre, vuelve sola a
la anterior. El cuadro de actualización ofrece *Abrir página*. *Canal de
actualización*, en *Preferencias*, categoría
*General*, elige si se ofrecen solo versiones estables o también las beta.

## Problemas frecuentes

### No hay voces

Agrega una voz en *Configuración, Hora e idioma, Voz*, o elige el motor
OneCore en *Preferencias*, categoría *Voces*. Las voces neurales de Windows
11 no aparecen en SAPI 5.

### «Windows protegió tu PC»

El aviso aparece porque el ejecutable no está firmado. Elige *Más
información* y después *Ejecutar de todos modos*.

### El antivirus avisa

Es un falso positivo frecuente en las aplicaciones que se distribuyen sin
instalador. Agrega la carpeta de Guyrapu a las exclusiones del antivirus.

### El chat no se ve en el vídeo

*Anunciar estado* dice si el chat en el vídeo está activo y si OBS lo
muestra. Si OBS no lo muestra, revisa la fuente en la pestaña *Escena* del
*Panel de OBS*.

### Informar de un error

*Abrir carpeta de registros*, en el menú *Ayuda*, abre la carpeta `data`.
Reproduce el problema y envía los archivos `guyrapu.log`,
`guyrapu-debug.log` y, si Guyrapu se cerró solo, `guyrapu-fallos.log`.

## Licencia

Guyrapu se distribuye con la licencia GPL-3.0. Consulta el archivo
[LICENSE](../../LICENSE).
