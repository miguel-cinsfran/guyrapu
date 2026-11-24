<!-- original: es/MANUAL.md 7aa88bf1a9c672b854f091e0853fe3627d88d094 -->
# Guyrapu, user manual

This is a translation of the Spanish original, made with artificial intelligence. If you find an error, report it at https://github.com/miguel-cinsfran/guyrapu/issues. See the [original in Spanish](../es/MANUAL.md).

Guyrapu reads the chat of YouTube and TikTok live streams aloud, and controls OBS Studio and Restream from the keyboard. It is designed for people who are blind or have low vision and stream, and it is tested with NVDA.

Version 3.0.0 beta 9 · Windows 10 and 11 · [News](CHANGELOG.md)

## Installation

Extract the ZIP to any folder and open `Guyrapu.exe`. You do not need to install anything or have administrator permissions.

You need Windows 10 or 11, an internet connection and at least one Windows voice, which is added in *Settings, Time & language, Speech*. ElevenLabs is optional and requires your own account.

## The main window

When you open Guyrapu, the focus is in the *Link or ID* field. Paste the link of a live stream or a video and press *Connect*. The *Recent items* list offers the live streams you have already opened.

The window has three regions: *Connection*, *Content* and *Player*. In *Content* are the *Live chat*, *Comments* and *Information* tabs. Every change of region or tab is announced.

Menu commands that open a dialog end with an ellipsis. *Go to the live chat*, *Go to comments* and *Go to the player* are written in lower case after “Go to”. Test dialogs have the *Start* button, and in music the command is *Rename playlist*. The *Cancel* and *Close* buttons have access keys, like the other commands.

`F1` opens the manual at the section for the open window. When you open the history, OBS, Restream or the profile settings, the focus lands on the first useful control.

Buttons and lists that are loading or waiting stay in the Tab order and say what is happening: *Load lists* says it is loading, *Capture* says whether it is loading the sources or capturing, *Send* says it is waiting, *Check key* says it is checking, and *Quality* says when the format has no quality. *OK* says why there is nothing to choose in source dialogs, and an empty list says why. OBS actions without a connection stay in the Tab order, say “no connection with OBS” and warn that OBS is not connected when you press them. With a chat connected, the link field stays in the Tab order and you can read it; to change it you have to disconnect. Waits sound while they last and play a done or error sound at the end.

| Key in the Recent items list | Action |
|---|---|
| `Enter` | Open the live stream |
| `Delete` | Remove it from the history |

## <a id="chat"></a>The chat

Each message is read with the chosen voice and has a sound according to who writes (channel owner, moderator, verified account or member) and according to what it is (Super Chat, membership or TikTok gift). YouTube Super Chats and stickers sound according to their amount, with the same three TikTok gift sounds: small, medium and large.

With *Translate chat*, in the *Chat* menu and in *Preferences*, on the *Reading* category, messages in other languages are read and shown translated, with the original language at the end. It is off by default.

If the chat drops on its own in the middle of a live stream, it sounds like a disconnection, and when it comes back, like a reconnection. It is different from connecting or disconnecting it by hand.

In the chat list, the arrows move from one message to another, and when you type a few letters the focus jumps to the first author that starts that way. The context menu copies the message, mutes the author for the session and assigns an alias. With the Google session started, it also puts the author in timeout or hides them from the channel. A sound plays at the beginning or the end of the list. The menu shows the key of each action, and `Shift+F10` opens it too.

Messages that are commands, such as `!discord`, or votes, such as `!1`, have their own reading mode in *Preferences*, on the *Live events* category. By default they appear in the list without being read.

When the chat is full, the discarded messages notice says they are in the chat list and that `F10` raises the voice speed to keep up. It does not recommend reading only the name.

*Search chat…*, in the *Chat* menu or with `Alt+B`, finds text in the messages of the live stream and jumps to the message. *Chat participation…*, in the same menu or with `Alt+P`, shows how many messages each person wrote, adds up their gifts and Super Chats, can be sorted by gifts and saves the summary as text, to thank people at the end of the live stream.

On TikTok, Guyrapu only reads: TikTok does not offer an official way to comment or moderate. Names with decorative letters are read as plain text, each new follower is announced once per live stream and comments are not repeated when it reconnects.

With a Restream profile that reads the YouTube chat and the TikTok chat, both arrive in the same list and each row says which platform it is from. When the live stream starts, the TikTok chat may take a while to connect: Guyrapu waits up to 3 minutes and warns once that TikTok does not let the chat be read yet. In *Preferences*, on the *Live events* category, *Each platform's own sound* chooses whether TikTok messages always have their sound, only with several chats or never, and *Announce which platform each message has when there are multiple chats* makes the voice say it too.

### Live events

Joins, likes, followers, gifts, polls, goals and TikTok battles are configured in *Preferences*, on the *Live events* category. Each event has a list with these modes:

- *Main voice and sound* and *Secondary voice and sound*: it appears in the list, plays a sound and is read with that voice.
- *Main voice without sound* and *Secondary voice without sound*: it appears and is read with that voice, without its sound.
- *Sound only*: it appears and plays a sound, without being read.
- *List only*: it appears without sound and without being read.
- *Off*: it does not appear.

*Group joins* and *Group likes* bring together in one row what arrives in a few seconds, such as “Ana, Beto and Caro joined”. With *Notify the first join immediately*, on by default, the first person to join is announced immediately and only those arriving during the wait are grouped.

### Reading format

The format decides which part of the message is read. It is chosen in *Preferences*, on the *Reading* category.

| Format | Example |
|---|---|
| Name and message | “Lucía: hello everyone” |
| Message then name | “hello everyone, from Lucía” |
| Message only | “hello everyone” |
| Name only | “Lucía” |

The words and users that are not read are written in the *Filters* category.

### Alias

An alias changes how an author's name is read, for example one made of letters and numbers. In the context menu of a message, choose *Assign alias to <author>…*. The alias also applies to previous messages, and moderation still acts on the real account. To remove it, leave the field empty.

### Writing in the chat

The *Message* box comes after the chat list. To write you need the Google session and a YouTube live stream with the chat open. If something is missing, the *Send* button says so in its name. Each message accepts up to 200 characters.

| Key in the Message box | Action |
|---|---|
| `Enter` | Send the message |
| `Shift+Enter` | Insert a line break |

On a published video, the *Comments* tab reads the comments, and with the Google session it lets you comment and reply. *Load more* and *Reload comments* can always be reached with `Tab` and say why they cannot do anything. In the list, *Reply…* always appears: without a Google session it says why it cannot be used, and `Shift+F10` opens the menu with the key of each action.

## <a id="voces"></a>Voices and sounds

Guyrapu reads with SAPI 5 and OneCore, which come with Windows, and with ElevenLabs, which requires an account. Phonon and Piper voices are installed from *Manage voices*, in the *Voice* menu or from the button of the same name in *Preferences*, on the *Voices* category, and appear in that category once installed. The engine and the voice are chosen there. The speed, the volume and the pitch are adjusted with wide sliders, like the slider for the music volume and the one for the media volume. *Test voice* plays a sample with any engine. Local voices say their language. The secondary voice can use another engine. If a local voice fails or ElevenLabs fails because of the network or a lack of balance, Guyrapu reads with the *Backup Windows voice* and warns you once. With Phonon or Piper you also choose the audio output of the chat voice, for example headphones, so it does not go into the live stream. The voice is chosen in *Preferences*, on the *Voices* category: the *Voice* menu has no submenu for choosing a voice.

Each type of message, event and notice has its sound. In the *Sounds* category you choose the theme, *Default* or *Soft*, and turn off each sound separately. The page shows the sounds grouped by family and says the family of each one. It has a context menu with *Play sound*, plays a sound at the edge with the arrows and searches as you type, like the other lists. In English, the names come translated. Waits sound while they last and play a done or error sound at the end: loading the live stream lists of YouTube, adding a capture to the AI, asking OBS for the microphone, connecting Restream, signing in to YouTube, checking keys in *Preferences*, loading the music folder and checking for updates. The wait sound plays when connecting and in the other waits, and does not sound like the disconnected sound.

*Voice licenses*, in the *Help* menu, opens the license of each voice pack you can download in the browser.

### Manage voices

*Manage voices…*, in the *Voice* menu, opens the window of the same name. You can also open it with the *Manage voices…* button in *Preferences*, on the *Voices* category. With `Tab` you move through the controls in this order: *Language*, *Voice engine*, *Search voice*, *Voices*, *Details*, *Install*, *Update*, *Remove*, *Preview voice* and *Close*. In *Search voice*, the down arrow moves to the voice list without leaving the box. In *Voices* you can select several rows: `Enter` plays the preview and `Delete` removes the chosen packs.

To install one or several voices, select them in *Voices* and choose *Install*. The chosen voices are downloaded and installed together, with a single wait that you can cancel. Phonon installs all the voices for the language together, because the pack is the whole language. *Update* and *Remove* act on the packs already installed, and *Remove* asks for confirmation.

Each row in *Voices* says the name of the voice, its gender, its language, the quality or age published by the engine, the status of the pack and a notice when the license limits use. *Details* shows the name of the pack, its engine, the quality of each Piper voice, the age of each Phonon voice, the language, the number of voices, the size, the status, the license and the use. The quality of Piper voices can be very low, low, medium or high. The age of Phonon voices can be young, young adult, adult, middle-aged or older adult.

The use of each pack appears in the row as a notice and in *Details* with a sentence: «Use: free, commercial use allowed.», «Use: non-commercial only. A live stream with income is commercial use.», «Use: research only. The voice comes from data with a research license.» or «Use: not confirmed. The voice's model card does not state its license or the data it comes from.». The license of each pack is in *Details*, with its link, and in *Voice licenses*, in the *Help* menu.

*Preview voice* plays the sample of the chosen voice, like `Enter` in the list. With Phonon, the preview uses the longest sample of each voice.

### Sound families

The families appear in this order, and each one says what kind of notice plays with it:

- *Completed*: what you asked for worked. *Text copied* plays `copiar.wav`, and the rest of the family uses the same file: *Action completed*, *Voice changed*, *Message sent*, *Comment posted*, *Moderation action*, *Reading queue cleared*, *Clip saved*, *Screenshot added*, *Search with results*, *Search without results*, *Download added to the queue* and *Update ready to install*.
- *Error*: what you asked for could not be done. *Error* plays `error.wav`, and the rest of the family uses the same file: *AI error*, *Search failed*, *Formats unavailable* and *Black screenshot detected*.
- *In progress*: something is running or waiting. *Waiting* plays `espera.wav`, and the rest of the family uses the same file: *Connecting*, *Player busy*, *Query sent to the AI*, *Search in progress*, *Loading formats*, *TikTok is limiting queries* and *Preparing the broadcast*.
- *On*: something turns on or comes back. *Reading resumed* plays `reanudar.wav`, and *Connected*, *Recording started* and *Recording resumed* use the same file.
- *Off*: something turns off or stops. *Reading paused* plays `pausa.wav`, and the rest of the family uses the same file: *Chat disconnected*, *Recording stopped*, *Recording paused*, *AI query canceled* and *Download canceled*.
- *Warning*: something is worth checking. *General alert* plays `aviso.wav`, and the rest of the family uses the same file: *Recording problem*, *Other Restream destinations*, *Global shortcuts already in use* and *Weak Restream signal*.
- *Disconnected*: something live drops or stops responding. *Broadcast problem* plays `transmision_problema.wav`, and the rest of the family uses the same file: *Reconnecting the live stream*, *Live stream with repeated interruptions*, *Restream destination disconnected*, *No Restream signal*, *Chat disconnected*, *OBS is not responding* and *Playback interrupted*.
- *Reconnected*: that same thing comes back. *Broadcast restored* plays `transmision_recuperada.wav`, and the rest of the family uses the same file: *Restream destination back*, *Restream signal restored*, *Chat reconnected* and *OBS is responding again*.
- *Broadcast and live stream*: the state of the broadcast and the live stream. *Live stream in progress* plays `al_aire.wav`, *Broadcast stopped* plays `transmision_detenida.wav`, *Live stream ended* plays `fin_directo.wav`, *TikTok live stream paused* plays `directo_pausado.wav` and *TikTok live stream continues* plays `directo_reanudado.wav`. *Live stream close confirmed* and *Playback finished* use the one of their family, `fin_directo.wav`.
- *Chat*: the messages and events of the chat. *New chat message* plays `mensaje_nuevo.wav`, *TikTok message* plays `mensaje_tiktok.wav`, *Channel owner message* plays `mensaje_propietario.wav`, *Moderator message* plays `mensaje_moderador.wav`, *Message from a verified account* plays `mensaje_verificado.wav`, *Message from a channel member* plays `mensaje_miembro.wav`, *Super Chat* plays `superchat.wav`, *New channel member* plays `nuevo_miembro.wav`, *New live stream follower* plays `seguir.wav`, *Someone shared the live stream* plays `compartir.wav`, *Gift chest received* plays `cofre.wav`, *Live stream like* plays `me_gusta.wav`, *Small gift or Super Chat* plays `regalo_chico.wav`, *Medium gift or Super Chat* plays `regalo_mediano.wav`, *Large gift or Super Chat* plays `regalo_grande.wav`, *Someone joined the live stream* plays `entrada.wav`, *Poll opened* plays `encuesta.wav`, *Poll ended* plays `encuesta_fin.wav`, *Goal reached* plays `meta.wav`, *Battle started* plays `batalla.wav` and *Battle ended* plays `batalla_fin.wav`.
- *Downloads*: the progress and result of downloads. *Download progress* plays `descarga_avance.wav`, and *Download started* and *Processing download* use the same file. *Download stalled* plays `descarga_quieta.wav`, *Download completed* plays `descarga_completada.wav`, *Download failed* plays `descarga_fallida.wav`, *Partial download* uses `descarga_fallida.wav` and *Download queue finished* plays `cola_descargas_terminada.wav`.
- *Artificial intelligence*: the queries and answers of the AI. *The AI is analyzing* plays `ia_analizando.wav` and *AI response* plays `ia_respuesta.wav`.
- *Music*: what happens with the songs. *Song changed* plays `musica_tema.wav`, *End of the music queue* plays `musica_fin.wav`, *Error playing the song* plays `musica_fallo.wav`, *Volume matching* plays `musica_igualando.wav` and *Volume matching complete* plays `musica_igualada.wav`. *Song changed* is set in *Preferences*, on the *Sounds* category, and not on *Music*. If you had it checked you still hear it; in new installations that sound and the end of the music queue sound are off.
- *Indicators*: the notices of the lists, the framing and the microphone. *Start or end of a list* plays `orilla.wav`, *Face outside the frame* plays `encuadre_fuera.wav`, *Face back in the frame* plays `encuadre_dentro.wav`, *Microphone level good* plays `microfono_bien.wav`, *Microphone level to check* plays `microfono_revisar.wav` and *No microphone signal* plays `microfono_sin_senal.wav`.
- *Application*: the start of Guyrapu and the updates. *Application start* plays `app_inicio.wav` and *Update available* plays `actualizacion_disponible.wav`.

### Your own theme

To make your own theme, copy the `sounds/themes/default` folder with another name. A file with the name of an event plays for that event, for example `superchat.wav`. If the theme does not bring that file, the one of its family in the same theme plays and, if that is missing too, the one of the default theme. That way you can change only the sounds you want.

## Player

The live stream video plays inside Guyrapu, with the commands in the *Player* menu. In a live stream, each jump says the distance to the live stream, for example “40 seconds behind the live stream”, and on YouTube you can go back up to an hour. If the connection fails, Guyrapu reconnects at the same point. If the process that joins the video and the audio crashes, Guyrapu opens it again on its own and keeps playing instead of staying silent.

With the focus on the video, the `0` through `9` keys move the position to 0, 10, 20 and up to 90 percent of the video, as on YouTube. Guyrapu announces the position it moved to.

*Play sound only, without the picture*, in *Preferences*, on the *Player* category, is checked: without the picture, jumps are almost immediate.

## <a id="musica"></a>Music

Guyrapu plays music while you stream. It uses the Music folder next to the application, or the one you choose in *Preferences*, on the *Music* category. The commands are in the *Music* menu, and *Choose music…* opens the *Music* window:

- *Collections* shows the *Library*, which is your folder, and your playlists.
- *Find* filters while you type, also without accents.
- *Songs* has a context menu to play now, next or to the end, and to add to the queue or to a playlist.
- *Show the queue* shows what is going to play.
- *Open link…* adds a YouTube video or playlist to the queue.

In *Songs*, in the queue and in the search results you can select several songs with `Shift` and the arrows, `Ctrl+Space` or `Ctrl+A`. *Play*, *Add to the queue*, *Add to the playlist* and *Delete* act on all of them with one announcement. Actions that need a single row stay in the menu and say why they cannot be used. `F2` renames the playlist chosen in *Collections*. Replaying a YouTube song starts at once. If a song does not open with the stored address, Guyrapu asks for it again before skipping it.

*Mute the music*, in the *Music* menu, does the same as `Ctrl+Alt+M`. With *Use keyboard media keys*, the play, pause and next or previous song keys control the music while there are songs in the queue, and the Windows media panel shows what is playing. Turn it off in *Preferences*, on the *Music* category.

When you create or edit a playlist, a dialog with two lists opens. In *Playlist songs*, `Delete` removes the song and `Alt+Up Arrow` and `Alt+Down Arrow` move it. *All songs* shows the folder with a checkbox for each song, checked for the ones already in the playlist: checking or unchecking it adds or removes the song. Its menu has the Applications key and *Add all to the playlist*, which adds all the songs shown by the search at once, and `Ctrl+A` selects all. In both lists, `Enter` plays the song.

The music volume is adjusted with a slider in *Preferences*, on the *Music* category, like the player volume. On that same category, *Lower music while the voice speaks* and *Lower music while media plays* lower the music on their own while either happens, and *Music volume when lowered* sets the volume it lowers to. By default it lowers with media and not with the voice.

*Match song volume* makes them all sound at a similar volume. Each file is measured once, with the *Match the volume* button in the *Music* window, and it is not modified. When it finishes, a sound plays and it says how many songs were matched. When you open Music, the box that offers to match has the *Do not ask again* button. Between one song and the next there is a crossfade, which is adjusted in *Crossfade between songs, in seconds*.

With *Use music shortcuts in any application*, the music shortcuts also work in OBS or in a game, and those keys stop reaching the other applications.

Where NVDA detects a table, as in File Explorer, it keeps Ctrl+Alt and the arrows. In that case, press NVDA+F2 before the shortcut.

## Going live

Guyrapu starts and ends the live stream with OBS Studio, to YouTube or to several platforms at once with Restream.

### Before going live for the first time

- Turn on the OBS WebSocket server in *Preferences*, on the *OBS* category.
- For YouTube, start the Google session and enable live streams on your channel.
- For Restream, connect the account and create a profile. See [Restream](#restream).
- So that OBS uses a different profile when broadcasting horizontally, vertically or recording, assign them on the *Profiles* tab of the *OBS panel*. See [OBS profiles](#obs-profiles).

If OBS is closed, Guyrapu opens it in the notification area. Before broadcasting, if the NVDA screen curtain would leave a screen capture black, Guyrapu warns, says how to fix it and offers to change the capture method to Windows 10.

### <a id="transmitir"></a>Starting the live stream

1. Press *Broadcast live*, next to *Connect*. The *Broadcast to* dialog opens, with the destination from last time already chosen.
2. Choose *YouTube* or a Restream profile and press *Continue*.
3. Guyrapu prepares OBS and checks the scene: whether it is empty, whether an
   image comes out black or whether the microphone is muted. If you choose
   *TikTok* and the OBS profile has no stream key, it warns and says where to
   write it in OBS. If it finds a
   problem, the button chosen by default is *Cancel*. If you broadcast to
   TikTok and the Restream account is also going to send the live stream to
   other enabled destinations, the confirmation before starting says so, with
   its own sound and the focus on *Cancel*, and suggests choosing a Restream
   profile. If something fails when starting, the error always appears in a
   box.
4. For YouTube, or a profile with YouTube, type the title, the description and the privacy. The rest of the data is optional, and Guyrapu remembers the last thing you typed. To do tests, use *Unlisted*.
5. When the live stream starts, Guyrapu connects the chat and announces it.

If the internet connection is lost, YouTube waits for it to come back without ending the live stream. Closing Guyrapu does not interrupt the live stream, and when you open it again it recognizes it. If Guyrapu closed with no connection and a YouTube live stream still open, it warns when you open it again and ends the live stream on its own when the connection comes back, even if the application stays closed. When you broadcast to YouTube and TikTok at the same time, *Copy live stream link* copies both links, one below the other.

During the live stream, the button is called *End live stream* and asks for confirmation, with *Keep broadcasting* chosen by default. When it ends, Guyrapu says how many frames were dropped, whether it was due to the network, the encoder or the drawing of the scene, and what to change in the profile for the next one. OBS goes back to the profile it had before the live stream, also if you cancel it before it starts.

### <a id="microfono"></a>Microphone

*Mute OBS microphone*, in the *OBS* menu, mutes or turns on the microphone. When you turn it on, Guyrapu says which device it uses and warns if no sound comes in. To set the device, use *Choose a device…* on the *Audio* tab of the *OBS panel*.

### Recording and saving clips

With *Record while broadcasting* checked, in the *Broadcast* menu, OBS records for as long as the live stream lasts. If the recording cannot start, the live stream continues and a warning plays. To record without broadcasting, use the *OBS* menu or the *Recording* tab of the *OBS panel*.

*Save clip* saves the last 30 or 60 seconds, according to the *Clips* list in *Preferences*, on the *OBS* category. With *Allow {comando} in chat*, anyone in the chat saves a clip by typing `!clip`, with a wait between clips that is chosen in the same category.

When you stop a recording or save a clip, Guyrapu says the file name.

### Chat on video

The chat on video shows the messages and gifts over the live stream image, for the viewers, with a color for each person. It is added with *Add source…*, *Chat on video…*, on the *Scene* tab of the *OBS panel*. In another streaming application, such as Streamlabs, it is added as a browser source with this link:

    http://127.0.0.1:8730/chat

## <a id="panel-obs"></a>OBS panel

The *OBS panel* brings together in tabs what is done with OBS, and it is opened from the *OBS* menu. If OBS is closed, the panel opens it. Everything can still be done in OBS, and the OBS plugin for NVDA still works.

### General

*Status* summarizes the broadcast, the recording, the current scene, the microphone and the computer usage. *Show OBS* brings the OBS window to the front, also from the notification area. If OBS takes a while to connect or stops responding for a moment, it warns and keeps looking after the live stream instead of giving up, with the disconnection sound and the reconnection sound when it comes back. The panel keeps responding while it waits for OBS and can be closed at any time. With a live stream on air, problem notices do not open a box over the game. *Close OBS*, also in the *OBS* menu, closes OBS without forcing it, so it does not ask about safe mode when you open it again. If OBS is broadcasting or recording, it does not close it and warns.

*Test computer…* records for a few seconds with the profile in use to see whether the PC drops frames. If it does, it tries lighter settings until it finds some that work and offers to save them in the profile. With the Aitum Vertical Canvas plugin in OBS, the dialog offers to include the vertical canvas, to know whether the PC can broadcast in both orientations at the same time. Test recordings are deleted at the end.

*Test connection…* does a private test live stream on YouTube, which nobody sees and which deletes itself, to know what bitrate your connection supports, and offers to save it in the profile. It needs the Google session.

The computer and connection tests show their progress in a window, with a wait sound, and if they fail they leave the error written in it. The result closes with `Esc`. In the connection test, if an attempt fails with an OBS error, Guyrapu tries again and continues with the next one. If the YouTube session expired, it says so and explains how to start it again.

### Scene

The *Scenes* list shows each scene, whether it is the current one and how many sources it has. Browsing it does not change what is broadcast: *Change scene* puts the chosen scene on air, and *Add scene…* creates a new one. It plays a sound at the edge and double-click changes the scene.

*Create vertical version*, in the context menu of a scene, creates a copy with the same name followed by “vertical”, with the same sources and a vertical layout. When broadcasting vertically, that copy goes on air, and at the end the scene that was there comes back.

The *Sources* list shows the sources of the chosen scene. Each row first says whether the source has a problem (hidden, covered or outside the video), then where it is, with the same words as the size and position dialog, and what part of the video it occupies. If a source does not fit, it suggests *Apply layout* to fit it. The context menu of each row brings together its actions. *Size and position…* places it in one of nine positions, with a size from one fifth to the full width of the video, and *Move with arrows* moves it in steps. If the scene has no sources, the list says so and explains how to add one.

*Add source…* adds to the scene a camera, a window, game or screen capture, an image, a media file, a text, the chat on video or a source from another scene.

*Apply layout…* distributes the whole scene at once. It comes with three
factory layouts, *Full screen*, *Picture-in-picture* and *Split in two*, and
the dialog lets you choose which source goes in each place, the corner, the
split and the chat. *Fit* decides what happens if the aspect ratio does not
match: *Fit* shows the whole source, *Cover* crops the edges and *Automatic*
fills with the camera and fits the rest. *Save as…* saves your own layout. In the menu for transforming a source, *Fit to the video* makes it grow to fill the video, as in OBS.
On a vertical canvas, *Split in two* stacks the sources at the top and
bottom, and the chat in a strip goes at the bottom.

*Undo all changes* returns the scene to how it was when the panel was opened.

| Key in the Scenes list | Action |
|---|---|
| `Enter` | Change to that scene |
| `F2` | Rename |
| `Ctrl+D` | Duplicate |
| `Delete` | Delete |

| Key in the Sources list | Action |
|---|---|
| `Space` | Show or hide the source |
| `Alt+Enter` | Properties |
| `F2` | Rename |
| `Ctrl+D` | Duplicate |
| `Delete` | Delete |
| `Ctrl+Home` / `Ctrl+End` | Bring to front or send to the back |
| `Ctrl+Up Arrow` / `Down Arrow` | Bring forward or send backward |
| `Ctrl+Z` | Undo |

| Key in Move with arrows | Action |
|---|---|
| Arrows | Move 10 pixels |
| `Ctrl` and arrows | Move 50 pixels |
| `Shift` and arrows | Move 1 pixel |
| `Enter` | Confirm |
| `Esc` | Undo the move |

### OBS profiles

The *OBS profiles* list shows each OBS profile, its orientation and what it is used for: broadcasting horizontally, broadcasting vertically or recording.

- *Use this profile* switches OBS to that profile.
- *Use for…* chooses what it is used for. The same is chosen in *Preferences*, on the *OBS* category, where *The profile OBS is using* leaves OBS as it is.
- *New…*, *Duplicate…* and *Delete profile* create, copy and delete profiles.
- *Edit settings…* changes the canvas, the output, the frames per second, the encoder, the broadcast, the recording, the clip buffer and the audio, including the monitoring device.
- *Prepare profiles…* creates a profile for broadcasting horizontally, another one vertically and another one for recording, checks which settings work well on your PC,   assigns them and says what it did. The profiles you already had do not change. It shows its progress in a window, with a wait sound, and if it fails it leaves the error written in it. The summary closes with `Esc`.

When broadcasting or recording without a live stream, Guyrapu switches OBS to the assigned profile, and at the end it goes back to the one it had. Editing the settings of a profile that is not in use does not change the OBS profile. When it changes profiles, Guyrapu first matches the audio of the destination profile to the one of the profile in use, so OBS does not ask to restart.

With no profiles, the list says how to create one. *New…* creates the profile and opens its settings. In the list, `Delete` removes the profile, `Enter` opens its settings and the Applications key opens a menu with the same actions as the buttons.

### Broadcast

*Broadcast live* opens the *Broadcast to* dialog, the same as the button in the main window, and *Restream…* opens the Restream window. During the live stream, *End live stream* ends it in the same way as that button, including the YouTube live stream.

### Audio

The *Audio sources* list shows each source with its status and its filters. If there are no audio sources, the list says so. The buttons act on the chosen source:

- *Mute* mutes or turns it on.
- *Test level* says every five seconds whether the level is right, low or high, or whether it is clipping, until you press *Stop test*.
- *Filters…* turns on noise suppression, the noise gate and gain. If OBS already had one of those filters, that one is used.
- *Listen* lets you hear the source with its filters through the OBS monitoring device. Use headphones to avoid feedback.
- *Choose a device…* sets the microphone device.

### Recording

*Begin recording* and *Stop recording* record without broadcasting, and *Pause recording* pauses the recording in progress: if there is none, it warns in the same way as the menu command. The *Recordings and clips* list brings together the recordings and the clips, from newest to oldest. It plays a sound at the edge, searches as you type and double-click opens the recording. Its context menu opens the file or its folder, copies the path or removes it from the list without deleting the file, and shows the key of each action. If OBS converts the recording to MP4 at the end, the list shows the MP4.

## <a id="restream"></a>Restream

Restream sends a single broadcast to several platforms at once. The Restream window opens with *Restream…*, in the *Broadcast* menu, and it has four tabs.

### Account

It shows the connected account and its destinations, and it lets you connect it, authorize it again or disconnect it.

### Destinations

It lists the channels of the account with their platform, and the disabled ones say so at the end. *Add destination…* opens the Restream page in the browser or adds a manual destination with server and key. The context menu of each destination turns it on or off, copies its link, opens it in the browser, changes its title or name, and deletes it. With no account connected, the list says how to connect it; with no destinations, it says how to add one.

### Profiles

A profile saves which destinations are broadcast to and with what orientation, and it appears with its name in the *Broadcast to* dialog. The list has a button for each action: *New profile…*, *Edit…*, *Rename…*, *Duplicate* and *Delete*. With no profiles, it says how to create one. In the profile:

- *Orientation* is *Horizontal*, *Vertical* or *Horizontal and vertical at the same time*.
- *YouTube, the channel of your Google session* adds that channel, with the live stream that Guyrapu creates from the data you type when you broadcast.
- *Chat that Guyrapu reads* chooses which chat is read if the profile has YouTube and TikTok. With *YouTube and TikTok*, which comes chosen in new profiles, both are read.

### Horizontal and vertical at the same time

With the *Horizontal and vertical at the same time* orientation, the horizontal goes directly to YouTube and the vertical to the other destinations of the profile, such as TikTok. The profile must include YouTube, and the YouTube channels of the Restream account are turned off during the live stream, so that YouTube does not also receive the vertical.

The Aitum Vertical Canvas plugin in OBS is required. It is downloaded from github.com/Aitum/obs-vertical-canvas/releases and installed with OBS closed. The first time, Guyrapu adds the “Guyrapu” output to the plugin: if OBS is open, it says so, closes it and reopens it.

Before going on air, Guyrapu copies the vertical versions of your scenes to the vertical canvas, the ones that *Create vertical version* creates. During the live stream, when you change scenes, the vertical switches to the vertical version of that scene, and if it does not have one, it says so once. If the vertical is interrupted, a warning sounds and the horizontal continues: Guyrapu tries it again every 30 seconds and warns when it comes back. *End live stream* stops both.

### Events

*Show* chooses between upcoming events, those that are live and the history. *Event detail* shows its status, its times, its destinations and the description. The context menu copies the event links or information, offers *Open live* and adds the statistics to the detail. If there are no events for the chosen filter, the list says so.

### Warnings during the live stream

With a Restream profile, Guyrapu warns with its own sound when Restream stops receiving the OBS signal and when it recovers it, when the signal is weak and when a destination disconnects or comes back.

## Camera framing

If the current scene has a camera, Guyrapu says how it sees you: how many faces there are, whether you are centered, far away, sideways or outside the edge, whether light is missing or there is backlight, and whether the image froze. Left and right are said as the movement you have to make: “Move to your left.”. The image is analyzed on the computer and is not sent anywhere.

The commands are in the *OBS* menu:

- *Announce camera framing* says the framing. Twice in a row, it starts the guide with beeps, which sound from the side you have to move to, higher for up and lower for down. In the center a confirmation sounds.
- *Notify when the face leaves the frame* warns with a sound when the face leaves and with another when it comes back.
- *Show or hide the camera* hides the camera from the scene without turning off the device.

In *Preferences*, on the *Camera* category, you choose the OBS camera, the guide sound and whether left and right are inverted.

## Interaction

The *Interaction* window brings together what the audience sees and hears in the live stream. Open it with *Open Interaction…*, in the *Interaction* menu, or with `Ctrl+Shift+A`, and it opens again on the last page you used. It has a list of pages on the left and, on the right, the list and the actions of the chosen page.

The pages are split by when something comes out. *Commands* holds what the audience types, *Alerts* what happens in the live stream, and *Scheduled messages* what comes out on its own every so often. Then come *Polls*, *Questions* and *Goals*, and last *Media*, *Styles* and *Blocked words*. To open the help for the page in front of you, press `F1` or the *Help* button. Empty lists say what appears in them and how to add the first item.

### <a id="contenido"></a>Content

The command, alert and scheduled message dialogs share the *Content* section. It has five fields in this order: *Text*, *Show in*, *Media item*, *Seconds on screen* and *Style*. In *Text* you write what comes out and can use variables. *Show in* chooses *Video*, *Chat* or *Chat and video*. *Media item* chooses a file from the Media folder or *None*. *Seconds on screen* sets how long it stays on the video, and *Style* chooses how it looks. To save you need text or a media item. If it only goes to the chat, you need text and it cannot exceed 200 characters.

### <a id="comandos"></a>Commands

Commands are what the audience types in the chat. To create `!hola`, go to *Commands*, reach *Add* with `Tab` and press `Enter`. In *Word* type `!hola`, in *Text* type `Hello, thanks for being here` and in *Show in* choose *Chat and video*. Press *OK* and Guyrapu announces “Command added”. When someone types `!hola`, the audience sees the card on the video and the text in the chat, and the voice reads the chat message. `F2` says how many commands Guyrapu answered and which was the last one.

A command can also come out as sound only. Create `!applause` with *Word* `!applause`, leave *Text* empty and choose `applause.wav` in *Media item*. Leave *Show in* as *Video*. The audience hears the sound on the video and sees no card. Copy the file into the Media folder before you open the dialog so it appears in the list.

In *Location* you choose *At the beginning of the message* or *Anywhere in the message*. In *Alias* you type other words separated by commas, such as `hello, greeting`, that answer the same way. In *Permission* you choose *All*, *Moderators only*, *A list of names* or *Shortcut only*. The cooldowns *Wait between uses (seconds):* and *Wait per person (seconds):* limit the answers. In *Shortcut* you choose *None* or `Ctrl+Alt+Shift` plus a number from 1 to 9, and the command answers from any application. With *Shortcut only*, the command does not answer the chat and only answers that key. What used to be in "Triggers" as a command, word or shortcut moved only to this page.

*Pause commands*, in the *Interaction* menu, or `Ctrl+Alt+Shift+C` from any application, stops answering all of them at once. The list of commands the audience asks for is edited like any other command: its word, `!commands` by default and `!comandos` in Spanish and Portuguese, its text, where it appears and its style, and each command chooses whether it appears in the list.

### <a id="alertas"></a>Alerts

Alerts respond to what happens in the live stream: a Super Chat, a membership, a new follower or a TikTok gift. They used to be called "Triggers". To create a Super Chat alert, go to *Alerts* and press *Add*. In *Name* type `Thanks for the Super Chat`, in *Event* choose *Super Chats and gifts* and in *Minimum amount* type `5`. In *Text* type `Thanks, {usuario}, for {cantidad}.`, in *Media item* choose an image from the Media folder and in *Show in* choose *Chat and video*. Press *OK*.

When a Super Chat of 5 or more arrives, the audience sees the image and the card on the video and the text in the chat. Guyrapu writes the card in the chat and the voice reads the Super Chat. In *Test without a live stream*, the *Results* list says "The alert Thanks for the Super Chat responded". In *Permission and cooldown* you choose who can trigger it and how often, and the card can use `{usuario}`, `{cantidad}`, `{regalo}`, `{texto}` and `{contador}`. The part of the old triggers that answered commands, words or shortcuts is now in *Commands*. The check box *Notify when shown on video* makes the voice say, for example, "Alert Thanks for the Super Chat on video, from Ana." It is unchecked by default.

### <a id="mensajes-automaticos"></a>Scheduled messages

Scheduled messages come out on their own every so often, for example your social networks every ten minutes. To create one with an image, go to *Scheduled messages*, press *Add* and in *Name* type `Social networks`. In *Text* type `Follow me at @yourchannel`, in *Media item* choose `networks.png` and in *Show in* choose *Chat and video*. Leave `10` in *Minimum interval, in minutes* and press *OK*. With the Google session started and a YouTube live stream connected, the audience sees the image and the text on the video and the text in the chat, and the voice reads the message. `F2` says what is on the video.

You can also duplicate, sort, preview, export and import them. The ones that choose the video come in with an animation in OBS, stay for their time and leave one at a time, and respect *Chat messages in between*. YouTube usually blocks links: type the user name instead. If YouTube returns an error, the messages stop and Guyrapu warns you once. `Delete` or the context menu remove the chosen message.

### <a id="encuestas"></a>Polls

In *Polls* you prepare the question, the options, the duration and where the result appears. For example, type `Which game is next?`, add `One` and `Two`, set `2` as the duration and choose *Video*. Start the poll from Interaction. The audience sees the question on the video with the votes and the time, and votes by typing `!1` or `!2` from any chat. With `Ctrl+Alt+Shift+I` you hear the poll with its votes, and `Ctrl+Alt+Shift+E` closes it early. Without pressing any key, the voice says "10 seconds left in the poll." and, for example, "Uno is in the lead with 3 votes." when the leading option changes. The check box *Notify when 10 seconds remain and when the leader changes* silences these notices. It is checked by default.

### <a id="preguntas"></a>Questions

The audience leaves questions by typing `!pregunta` or `!q` in the chat. For example, type `!pregunta What is your channel called?` and the question goes into the queue, one per person. The *Questions* page shows the queue up to date. Select the question and press *Show on the video*: the audience sees it in the card. With `Ctrl+Alt+Shift+R` you hear the oldest one from any program. You can also mark it as answered, delete it or clear the queue. Each question has its own style.

### <a id="metas"></a>Goals

In *Goals* you prepare the goals of the live stream: what they count, how much is needed and the style and celebration they use. They count likes, followers, members, gifts or Super Chats. For example, create a follower goal with a target of `50`. When it is reached, a sound plays and the audience sees a card on the video with its celebration. You can show its fixed progress, for example «Followers: 12 of 50», and it is updated as they arrive. During the live stream, the voice says "Goal Followers: halfway, 25 of 50." and, at 90 percent, "Goal Followers: close to the target, 45 of 50." The check box *Notify at halfway and near the target* silences these notices. It is checked by default. TikTok like goals follow the number TikTok shows, including likes that arrived before you connected the chat.

### <a id="medios"></a>Media

The *Media* folder sits next to the application, like the Music folder. The *Open folder* button on this page opens it in File Explorer. Copy in an image file (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`), a video file (`.mp4`, `.webm`, `.mov`, `.mkv`) or a sound file (`.wav`, `.mp3`, `.ogg`, `.m4a`) and it appears in the list when you come back to the page. For example, copy `applause.wav` and press *Listen*: you hear the name and the description of the media item, and the sound or video plays. Press *Listen* again or `Esc` to stop it. The audience hears or sees it when a command or an alert shows it on the video. Media from earlier versions moves to this folder on its own the first time you open the application.

*Describe image* asks the artificial intelligence for a sentence about what the image or GIF shows, so that `F2` and the list say what the audience sees. Sounds and videos are matched in volume when added. The *Volume of the media in the video* slider balances them with the voice and the game. Each sound or video media item also has its own *Volume* in *Add media* or *Edit media*, from 0 to 200, which adds to the matching and the general volume. *Listen* plays it with that same gain, as on the live stream. When you choose a media item and press *Create command*, the command dialog opens already set up with that media item and a suggested name. When you accept, Guyrapu announces "Command added" and the command appears in *Commands*. You can also add, edit, duplicate, export and import media items; *Delete* also removes the file from the folder.

### <a id="estilos"></a>Styles

In *Styles* you create, duplicate, export and import styles for the messages on the video, with font, colors by name, background, area and animation. For example, create a style with a large font and a blue background, and press *Set as default…* to use it in commands. Each style can be the default for scheduled messages, commands, alerts, polls or goals, and each item can use the one for its type. *Test*, on this page and on *Scheduled messages*, builds the card off air and says where it appears, how much space it takes and whether there are font or contrast problems.

### <a id="palabras-bloqueadas"></a>Blocked words

In *Blocked words* you type the words that are hidden in the name and text of the audience shown by command replies. For example, add `spam`: if someone types `!hola spam`, the command card shows `***` instead of the word. Text made almost entirely of symbols is not displayed.

### <a id="probar-sin-directo"></a>Test without a live stream

*Test without a live stream…*, in the *Interaction* menu, and the *Test without a live stream* button in the window rehearse the interaction without going on air. You cannot open it with a live stream connected. In *Platform* you choose YouTube or TikTok. The *Type* changes with the platform: in YouTube you have *Message*, *Super Chat* and *Membership*; in TikTok, *Message*, *Gift*, *New follower*, *Likes* and *Shared live streams*. In YouTube *Role* also appears, with *Public*, *Moderator* and *Channel owner*. Type the author and what the type asks for, for example amount and message for a Super Chat, and press *Send*.

The *Results* list keeps a line for each send with the time, what you sent and what responded. For example: "The command !hola responded.", "The alert Thanks for the Super Chat responded.", "Vote counted in the poll", "Question added to the Questions page." or "Goal advanced to 12 of 50.". If nothing responded, the reason says why:

- "no command or alert uses that message." or "no alert uses that event.", when nothing matches.
- "the command is in cooldown, seconds left.", when its cooldown has not ended. The same is said of an alert.
- "the command is only for a permission.", when the permission does not include the author, and "the command is paused." or "commands are paused.", when they are stopped.

What goes to the video appears in OBS as in a live stream, without posting in the chats and without the voice reading it. Closing the window ends the rehearsal and discards what it left.


### Global shortcuts

The global `Ctrl+Alt+Shift` shortcuts of the interaction work even when another program has the focus: they pause, skip and clear what appears on the video, mute the media, turn on panic mode, turn scheduled messages on or off, pause commands, close the poll, read the next question and announce the interaction status. They are in the table [Keyboard shortcuts](#keyboard-shortcuts), in the family *Live interaction*.

## <a id="descargas"></a>Downloads and history

The *Download manager* downloads videos, audio or YouTube playlists in MP4, WebM, MP3 or M4A, two at a time. What is downloaded goes to the Downloads folder, next to the application. On the *Search on YouTube* tab, Space plays a result in the music without downloading it. *Show more* can always be reached with `Tab` and says when there are no more results. NVDA says the name of the results list and the downloads list. If a download stops making progress for two minutes, Guyrapu stops it and warns with an error, and *Retry* resumes it: if the connection was lost, the error says so instead of showing a code. Actions that do not work with the chosen download stay in the menu and say why. If downloads fail, use *Update yt-dlp…*, in the *Tools* menu.

The *Live stream history* shows what you watched, with a tab for YouTube and another for TikTok. Each list has a context menu, and an empty tab says there are no entries for that platform.

## Spoken status

*Announce status*, in the *View* menu, summarizes the connection, the live stream, the viewers, the messages read and the donations, with short and consistent sentences. When you broadcast to YouTube and TikTok at the same time, the viewers are those of both platforms. What is included is chosen in *Preferences*, on the *Status (F2)* category. Twice in a row, it opens the *Session status* window, with each piece of data on one line. `Ctrl+Alt+Shift+I` says how the live stream interaction is going: the poll with its votes, the battle, the goal, what appears on the video and how many questions are waiting. If there is nothing, it says so.

## <a id="ia"></a>Asking the AI

An artificial intelligence looks at an OBS screenshot and says what it sees, for example whether a source comes out black. It requires OBS open and a provider key.

In *Preferences*, on the *Artificial intelligence* category, you choose the provider, such as Google Gemini, OpenAI, Anthropic or OpenRouter, save the key and choose the model. When the list of models is updated, Guyrapu tests the chosen model with your key and warns if it does not respond or if it is paid. The key is kept in the Windows Credential Manager. If the key does not have the format Guyrapu expects, it warns you and offers to use it anyway, in case the provider changed the format.

*Ask the AI about the picture…*, in the *View* menu, opens a window where *Add screenshot* chooses the scene or a source, and also the frame of the video shown in the player, with OBS open or closed. The question is typed in *Message*. *Quick AI question* sends the current scene and reads the response without opening any window. `Ctrl+F2` and `Ctrl+Shift+F2` say the scene and its notices with short and consistent sentences, and the quick query warns if it is canceled. With OBS closed, `Ctrl+Shift+F2` describes the frame shown in the player; in audio-only mode there is no picture and it says so.

The conversation has a context menu, `Ctrl+C` copies the chosen message and a sound plays at the beginning or the end of the list. `Ctrl+S`, or *Save conversation…* in the menu of the *Conversation* list, saves the whole conversation to a text file. The AI quotes text in an image exactly as it is written, such as a sign, an alert or the chat inside the video. With the models that allow it, replies are more consistent from one query to the next.

The screenshot and what you type are sent to the provider, and the first send asks for confirmation. A black screenshot, such as the one left by the NVDA screen curtain, is not sent. In that case, change the capture method of that source to Windows 10 in OBS.

## Google session

The Google session lets you moderate, write in the chat, comment on videos and create the YouTube live stream. Without it, everything else works.

To start it, open *Preferences*, on the *YouTube* category, press *Sign in* and authorize in the browser. The YouTube and Restream sessions are saved encrypted with your Windows account: if you copy the application folder to another computer, you will have to start them again. YouTube's daily quota is shared among those who use Guyrapu. The estimated quota is kept up to date on its own with the costs Google publishes, once a week. To have your own, see the [API setup guide](../CONFIGURACION_API.md).

## <a id="preferencias"></a>Preferences

*Preferences…*, in the *Tools* menu, brings together the configuration by categories, and the changes are applied when you press *Save*. In *General* you choose the language and the update channel, and you export, import or reset the preferences. *Also show important notices in a message box* also shows the result of what you do in a box. Each category is prepared the first time you choose it, so the window opens faster.

Preferences are saved in `config.ini` and `sounds.ini`, in the `data` folder next to the application.

### Changing a shortcut

In the *Shortcuts* category, each action has a button with its shortcut. Press the button and then the new combination. If the combination is already in use or does not belong to that family, Guyrapu says why and keeps waiting. Fixed shortcuts can also be reached with `Tab`: their combination is read and, when you activate them, that they cannot be changed. *Reset shortcuts to factory defaults* returns to the original shortcuts.

| Key when changing a shortcut | Action |
|---|---|
| `Enter` | Leave the action without a shortcut |
| `Esc` | Cancel |

## Keyboard shortcuts

Each family of shortcuts uses its own modifier keys. They all also appear in the menu bar, next to their command. In action lists, typing the first letters jumps to the item that starts that way, a sound plays when you reach the beginning or the end, and the context menu shows the key of each action. `Shift+F10` opens that menu in the lists that have it.

### Fixed

| Shortcut | Action |
|---|---|
| `F1` | Open the manual at the section for the window |
| `F6` / `Shift+F6` | Next or previous region |
| `Ctrl+Tab` | Change tab |
| `Alt+F4` | Exit |

### Player (Ctrl)

| Shortcut | Action |
|---|---|
| `Ctrl+P` | Play or pause |
| `Ctrl+Left Arrow` / `Right Arrow` | Go back or forward 1 minute |
| `Ctrl+Up Arrow` / `Down Arrow` | Raise or lower the player volume |
| `Ctrl+End` | Go to the live stream |
| `Ctrl+D` | Stop playback |
| `Ctrl+M` | Mute or unmute the audio |
| `Ctrl+F` | Full screen |

### Chat (Alt)

| Shortcut | Action |
|---|---|
| `Alt+Enter` | Go to the writing box |
| `Alt+B` | Search chat |
| `Alt+P` | Chat participation |

### Windows (Ctrl+Shift)

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+P` | Preferences |
| `Ctrl+Shift+A` | Scheduled messages |
| `Ctrl+Shift+H` | Live stream history |
| `Ctrl+Shift+R` | Restream |
| `Ctrl+Shift+D` | Download manager |
| `Ctrl+Shift+M` | Music |
| `Ctrl+Shift+I` | Ask the AI about the picture |
| `Ctrl+Shift+O` | OBS panel |

### Live stream and OBS (Alt+Shift)

| Shortcut | Action |
|---|---|
| `Alt+Shift+C` | Connect |
| `Alt+Shift+D` | Disconnect |
| `Alt+Shift+L` | Go to the list of the current panel |
| `Alt+Shift+E` | Copy the live stream link |
| `Alt+Shift+I` | Mark an incident |
| `Alt+Shift+M` | Mute the OBS microphone |
| `Alt+Shift+G` | Start or stop recording |
| `Alt+Shift+P` | Pause or resume recording |
| `Alt+Shift+R` | Save a clip |
| `Alt+Shift+A` | Warn if OBS is overloaded |
| `Alt+Shift+O` | Show OBS |

### Voice and reading (F keys)

| Shortcut | Action |
|---|---|
| `F2` | Announce the status. Twice, open the list |
| `F3` | Announce the author of the last message |
| `F4` | Mute reading |
| `F5` | Pause or resume reading |
| `F7` | Mute sounds |
| `F8` | Stop the current voice |
| `F9` / `F10` | Lower or raise the voice speed |
| `F11` / `F12` | Lower or raise the voice volume |
| `Ctrl+F9` / `Ctrl+F10` | Lower or raise the voice pitch |
| `Ctrl+F2` | Describe the OBS scene |
| `Ctrl+Shift+F2` | Quick query |
| `Ctrl+F3` | Announce camera framing. Twice, guide with beeps |
| `Ctrl+Shift+F3` | Notify when the face leaves the frame |
| `Alt+F3` | Show or hide the camera |

### Live stream interaction (Ctrl+Alt+Shift)

| Shortcut | Action |
|---|---|
| `Ctrl+Alt+Shift+P` | Pause or resume the video queue |
| `Ctrl+Alt+Shift+S` | Skip the video message |
| `Ctrl+Alt+Shift+V` | Clear the video queue |
| `Ctrl+Alt+Shift+M` | Mute or turn on the media |
| `Ctrl+Alt+Shift+Q` | Turn panic mode on or off |
| `Ctrl+Alt+Shift+A` | Turn scheduled messages on or off |
| `Ctrl+Alt+Shift+C` | Pause or resume all chat commands |
| `Ctrl+Alt+Shift+E` | Close the poll |
| `Ctrl+Alt+Shift+R` | Read the next question |
| `Ctrl+Alt+Shift+I` | Interaction status |

The rehearsal *Test without a live stream…* and the global shortcuts are explained in [Interaction](#interaction).

### Music (Ctrl+Alt)

| Shortcut | Action |
|---|---|
| `Ctrl+Alt+Space` | Play or pause |
| `Ctrl+Alt+Right Arrow` / `Left Arrow` | Next or previous song |
| `Ctrl+Alt+Up Arrow` / `Down Arrow` | Raise or lower the volume |
| `Ctrl+Alt+Shift+Right Arrow` / `Left Arrow` | Go forward or back 10 seconds |
| `Ctrl+Alt+T` | Announce the current song |
| `Ctrl+Alt+M` | Mute or turn on |
| `Ctrl+Alt+D` | Stop |
| `Ctrl+Alt+A` | Shuffle |
| `Ctrl+Alt+R` | Change the repeat mode |

### Chat filter and recent messages (Ctrl+Shift)

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+-` | Previous chat filter |
| `Ctrl+Shift+=` | Next chat filter |
| `Ctrl+Shift+1` | Read the last message |
| `Ctrl+Shift+2` to `Ctrl+Shift+9` | Read from the second to the ninth from the end |
| `Ctrl+Shift+0` | Read the tenth from the end |

The two filter shortcuts use the keys to the right of zero and move through the chat list in menu order, wrapping at both ends. On a United States keyboard, these are `Ctrl+Shift+-` and `Ctrl+Shift+=`; on a Spanish keyboard, `Ctrl+Shift+'` and `Ctrl+Shift+¡` or `Ctrl+Shift+¿`.

With *Use chat shortcuts in any application*, in *Preferences*, on the *Reading* category, all these shortcuts also work when another application is in the foreground. If another application already uses one of these combinations, a tone sounds and Guyrapu says which one.

## Updating

*Check for updates…*, in the *Help* menu, says whether there is a new version, shows what is new and installs it. Guyrapu closes and opens again in about a minute, and keeps the `data` folder, the downloads and your own sounds. If the new version does not open, it goes back to the previous one on its own. The update dialog offers *Open the page*. *Update channel*, in *Preferences*, on the *General* category, chooses whether only stable versions are offered or beta versions too.

## Common problems

### No voices

Add a voice in *Settings, Time & language, Speech*, or choose the OneCore engine in *Preferences*, on the *Voices* category. Windows 11 neural voices do not appear in SAPI 5.

### “Windows protected your PC”

The notice appears because the executable is not signed. Choose *More information* and then *Run anyway*.

### The antivirus warns

It is a common false positive in applications distributed without an installer. Add the Guyrapu folder to the antivirus exclusions.

### The chat is not visible on video

*Announce status* says whether the chat on video is active and whether OBS shows it. If OBS does not show it, check the source on the *Scene* tab of the *OBS panel*.

### Reporting an error

*Open logs folder*, in the *Help* menu, opens the `data` folder. Reproduce the problem and send the files `guyrapu.log`, `guyrapu-debug.log` and, if Guyrapu closed on its own, `guyrapu-fallos.log`.

## License

Guyrapu is distributed with the GPL-3.0 license. See the [LICENSE](../../LICENSE) file.
