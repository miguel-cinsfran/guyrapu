# Guyrapu, manual de uso

Guyrapu lee en voz alta el chat de los directos de YouTube y TikTok, y
maneja OBS Studio y Restream desde el teclado. Está pensado para personas
ciegas o con baja visión que transmiten, y se prueba con NVDA.

Versión 3.0.0 beta 2 · Windows 10 y 11 · [Novedades](CHANGELOG.md)

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

| Tecla en la lista Recientes | Acción |
|---|---|
| `Intro` | Abrir el directo |
| `Supr` | Eliminarlo del historial |

## El chat

Cada mensaje se lee con la voz elegida y lleva un sonido según quién
escribe (propietario del canal, moderador, cuenta verificada o miembro) y
según lo que es (Super Chat, membresía o regalo de TikTok).

En la lista del chat, las flechas pasan de un mensaje a otro, y al escribir
unas letras el foco salta al primer autor que empieza así. El menú
contextual copia el mensaje, silencia al autor durante la sesión y le asigna
un alias. Con la sesión de Google iniciada, también suspende al autor o lo
oculta del canal.

En TikTok, Guyrapu solo lee: TikTok no ofrece una forma oficial de comentar
ni de moderar.

### Eventos del directo

Las entradas, los me gusta, los seguidores, los regalos, las encuestas, las
metas y las batallas de TikTok se configuran en *Preferencias*, categoría
*Eventos del directo*. Cada evento tiene una lista con cinco modos:

- *Voz principal* y *Voz secundaria*: aparece en la lista, suena y se lee
  con esa voz.
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
la sesión de Google permite comentar y responder.

## Voces y sonidos

Guyrapu lee con tres motores de voz: SAPI 5 y OneCore, que vienen con
Windows, y ElevenLabs, que requiere una cuenta. El motor, la voz, la
velocidad, el volumen y el tono se eligen en *Preferencias*, categoría
*Voces*, donde *Probar voz* reproduce una muestra. Si ElevenLabs falla por
la red o por falta de saldo, Guyrapu lee con la *Voz de Windows de
respaldo* y lo avisa una vez.

Cada tipo de mensaje, evento y aviso tiene su sonido. En la categoría
*Sonidos* se elige el tema, *Predeterminado* o *Suave*, y se desactiva cada
sonido por separado. Para crear un tema propio, copia la carpeta
`sounds/themes/default` con otro nombre y reemplaza los archivos `.wav`.

## Reproductor

El vídeo del directo se reproduce dentro de Guyrapu, con los comandos del
menú *Reproductor*. En un directo, cada salto dice la distancia al directo,
por ejemplo «40 segundos por detrás del directo», y en YouTube se puede
retroceder hasta una hora. Si la conexión falla, Guyrapu reconecta en el
mismo punto.

*Reproducir solo el audio, sin imagen*, en *Preferencias*, categoría
*Reproductor*, viene marcada: sin imagen, los saltos son casi inmediatos.

## Música

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

*Igualar volumen de las canciones* hace que todas suenen con un volumen
parecido. Cada archivo se mide una vez, con el botón *Igualar volumen* de
la ventana *Música*, y no se modifica. Entre una canción y la siguiente hay
un fundido, que se ajusta en *Fundido entre canciones, en segundos*.

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

Si OBS está cerrado, Guyrapu lo abre en el área de notificación.

### Iniciar el directo

1. Pulsa *Transmitir en directo*, junto a *Conectar*. Se abre el cuadro
   *Transmitir a*, con el destino de la vez anterior ya elegido.
2. Elige *YouTube* o un perfil de Restream y pulsa *Continuar*.
3. Guyrapu prepara OBS y revisa la escena: si está vacía, si una imagen
   sale en negro o si el micrófono está silenciado. Si encuentra un
   problema, el botón elegido de entrada es *Cancelar*.
4. Para YouTube, o un perfil con YouTube, escribe el título, la
   descripción y la privacidad. El resto de los datos es opcional, y
   Guyrapu recuerda lo último que escribiste. Para hacer pruebas, usa *No
   listado*.
5. Cuando el directo empieza, Guyrapu conecta el chat y lo anuncia.

Si se pierde la conexión a internet, YouTube espera a que vuelva sin
terminar el directo. Cerrar Guyrapu no interrumpe el directo, y al volver a
abrirlo lo reconoce.

Durante el directo, el botón se llama *Finalizar directo* y pide
confirmación, con *Seguir transmitiendo* elegido de entrada.

### Micrófono

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

## Panel de OBS

El *Panel de OBS* reúne en pestañas lo que se hace con OBS, y se abre desde
el menú *OBS*. Si OBS está cerrado, el panel lo abre. Todo se puede seguir
haciendo en OBS, y el complemento de OBS para NVDA sigue funcionando.

### General

*Estado* resume la transmisión, la grabación, la escena actual, el
micrófono y el uso del equipo. *Mostrar OBS* trae al frente la ventana de
OBS, también desde el área de notificación.

### Escena

La lista *Escenas* muestra cada escena, si es la actual y cuántas fuentes
tiene. Recorrerla no cambia lo que se emite: *Cambiar escena* pone al aire
la escena elegida, y *Agregar escena…* crea una nueva.

La lista *Fuentes* muestra las fuentes de la escena elegida, y cada fila
dice dónde está la fuente, qué parte del vídeo ocupa y si se ve. El menú
contextual de cada fila reúne sus acciones. *Tamaño y posición…* la coloca
en una de nueve posiciones, con un tamaño de un quinto a todo el ancho del
vídeo, y *Mover con flechas* la mueve en pasos.

*Agregar fuente…* agrega a la escena una cámara, una captura de ventana, de
juego o de pantalla, una imagen, un archivo multimedia, un texto, el chat en
el vídeo o una fuente de otra escena.

*Aplicar diseño…* reparte toda la escena de una vez, con siete diseños de
fábrica, como la cámara en una esquina o dos fuentes lado a lado. *Ajuste*
decide qué pasa si la proporción no coincide: *Ajustar* muestra la fuente
entera, *Llenar* recorta los bordes y *Automático* llena con la cámara y
ajusta lo demás. *Guardar como…* guarda un diseño propio.

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

### Transmisión

*Transmitir en directo* abre el cuadro *Transmitir a*, igual que el botón de
la ventana principal, y *Restream…* abre la ventana de Restream.

### Audio

La lista *Fuentes de audio* muestra cada fuente con su estado y sus
filtros. Los botones actúan sobre la fuente elegida:

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
grabación* pausa la grabación en curso. La lista *Grabaciones y clips*
reúne lo grabado y los clips, del más nuevo al más antiguo. Su menú
contextual abre el archivo o su carpeta, copia la ruta o lo elimina de la
lista sin borrar el archivo.

## Restream

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
abre en el navegador, le cambia el título o el nombre, y lo elimina.

### Perfiles

Un perfil guarda a qué destinos se transmite y con qué orientación, y
aparece con su nombre en el cuadro *Transmitir a*. *Nuevo perfil…* crea
uno. En el perfil:

- *YouTube, el canal de tu sesión de Google* suma ese canal, con el
  directo que Guyrapu crea a partir de los datos que escribes al
  transmitir.
- *Chat que lee Guyrapu* elige qué chat se lee si el perfil tiene YouTube
  y TikTok.

### Eventos

*Mostrar* elige entre los eventos próximos, los que están en directo y el
historial. *Detalle del evento* muestra su estado, sus horarios, sus
destinos y la descripción. El menú contextual copia los enlaces o la
información del evento, abre el directo y agrega las estadísticas al
detalle.

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
- *Avisar si el rostro sale del encuadre* avisa con un sonido cuando el
  rostro sale y con otro cuando vuelve.
- *Mostrar u ocultar la cámara* oculta la cámara de la escena sin
  desactivar el dispositivo.

En *Preferencias*, categoría *Cámara*, se elige la cámara de OBS, el sonido
de la guía y si se invierten izquierda y derecha.

## Mensajes automáticos

Los mensajes automáticos se envían al chat cada cierto tiempo, por ejemplo
tus redes cada diez minutos. Se configuran en *Preferencias*, categoría
*Mensajes automáticos*, y funcionan en tu propio directo de YouTube con la
sesión de Google iniciada. YouTube suele bloquear los enlaces: escribe el
nombre de usuario en su lugar. Si YouTube devuelve un error, los mensajes
se detienen y Guyrapu lo avisa una vez.

## Descargas e historial

El *Administrador de descargas* descarga vídeos, audio o listas de YouTube
en MP4, WebM, MP3 o M4A, dos a la vez. Lo descargado queda en la carpeta
Descargas, junto a la aplicación. En la pestaña *Buscar en YouTube*,
Espacio reproduce un resultado en la música sin descargarlo. Si las
descargas fallan, usa *Actualizar yt-dlp*, en el menú *Herramientas*.

El *Historial de directos* muestra lo que viste, con una pestaña para
YouTube y otra para TikTok.

## Estado por voz

*Anunciar estado*, en el menú *Ver*, resume la conexión, el directo, los
espectadores, los mensajes leídos y las donaciones. Qué se incluye se elige en *Preferencias*,
categoría *Estado (F2)*. Dos veces seguidas, abre la ventana *Estado de la
sesión*, con cada dato en una línea.

## Preguntar a la IA

Una inteligencia artificial mira una captura de OBS y dice qué se ve, por
ejemplo si una fuente sale en negro. Requiere OBS abierto y la clave de un proveedor.

En *Preferencias*, categoría *Inteligencia artificial*, se elige el
proveedor, como Google Gemini, OpenAI, Anthropic u OpenRouter, se guarda la
clave y se elige el modelo. La clave queda en el Administrador de
credenciales de Windows.

*Preguntar a la IA sobre la imagen…*, en el menú *Ver*, abre una ventana
donde *Agregar captura* elige la escena o una fuente, y la pregunta se
escribe en *Mensaje*. *Consulta rápida a la IA* envía la escena actual y
lee la respuesta sin abrir ninguna ventana.

La captura y lo que escribas se envían al proveedor, y el primer envío pide
confirmación. Una captura en negro, como la que deja la cortina de pantalla
de NVDA, no se envía. En ese caso, cambia en OBS el método de captura de esa
fuente a Windows 10.

## Sesión de Google

La sesión de Google permite moderar, escribir en el chat, comentar vídeos y
crear el directo de YouTube. Sin ella, todo lo demás funciona.

Para iniciarla, abre *Preferencias*, categoría *YouTube*, pulsa *Iniciar
sesión* y autoriza en el navegador. La cuota diaria de YouTube se comparte
entre quienes usan Guyrapu. Para tener una propia, consulta la [guía de
configuración de la API](../CONFIGURACION_API.md).

## Preferencias

*Preferencias…*, en el menú *Herramientas*, reúne la configuración por
categorías, y los cambios se aplican al pulsar *Guardar*. En *General* se
elige el idioma y el canal de actualización, y se exportan, se importan o
se restablecen las preferencias. *Mostrar avisos importantes también en un
cuadro de mensaje* muestra además en un cuadro el resultado de lo que haces.

Las preferencias se guardan en `config.ini` y `sounds.ini`, en la carpeta
`data` junto a la aplicación.

### Cambiar un atajo

En la categoría *Atajos*, cada acción tiene un botón con su atajo. Pulsa el
botón y después la combinación nueva. Si la combinación ya está en uso o no
corresponde a esa familia, Guyrapu dice por qué y sigue esperando.
*Restablecer atajos de fábrica* vuelve a los atajos originales.

| Tecla al cambiar un atajo | Acción |
|---|---|
| `Intro` | Dejar la acción sin atajo |
| `Esc` | Cancelar |

## Atajos de teclado

Cada familia de atajos usa sus propias teclas modificadoras. Todos figuran
también en la barra de menús, junto a su comando.

### Fijos

| Atajo | Acción |
|---|---|
| `F1` | Abrir el manual |
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

### Ventanas (Ctrl+Mayús)

| Atajo | Acción |
|---|---|
| `Ctrl+Mayús+P` | Preferencias |
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
| `Ctrl+F2` | Describir la escena de OBS |
| `Ctrl+Mayús+F2` | Consulta rápida a la IA |
| `Ctrl+F3` | Anunciar el encuadre de cámara. Dos veces, guía con pitidos |
| `Ctrl+Mayús+F3` | Avisar si el rostro sale del encuadre |
| `Alt+F3` | Mostrar u ocultar la cámara |

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

### Mensajes recientes del chat (Ctrl+Mayús y número)

| Atajo | Acción |
|---|---|
| `Ctrl+Mayús+1` | Leer el último mensaje |
| `Ctrl+Mayús+2` a `Ctrl+Mayús+9` | Leer del segundo al noveno desde el final |
| `Ctrl+Mayús+0` | Leer el décimo desde el final |

Con *Leer mensajes recientes en cualquier aplicación*, en *Preferencias*,
categoría *Lectura*, estos atajos funcionan también con otra aplicación en
primer plano. Si otra aplicación ya usa una de estas combinaciones, suena
un tono y Guyrapu dice cuál.

## Actualizar

*Buscar actualizaciones…*, en el menú *Ayuda*, dice si hay una versión
nueva, muestra sus novedades y la instala. Guyrapu se cierra y vuelve a
abrirse en alrededor de un minuto, y conserva la carpeta `data`, las
descargas y los sonidos propios. Si la versión nueva no abre, vuelve sola a
la anterior. *Canal de actualización*, en *Preferencias*, categoría
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
