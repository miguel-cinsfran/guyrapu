<!-- original: es/MANUAL.md 479002f7d1e7df0d8afc910f357868aa2b14874a -->
# Guyrapu, user manual

This is a translation of the Spanish original, made with artificial intelligence. If you find an error, report it at https://github.com/miguel-cinsfran/guyrapu/issues. See the [original in Spanish](../es/MANUAL.md).

Guyrapu reads the chat of YouTube and TikTok live streams aloud, and controls OBS Studio and Restream from the keyboard. It is designed for people who are blind or have low vision and stream, and it is tested with NVDA.

Version 3.0.0 beta 3 · Windows 10 and 11 · [News](CHANGELOG.md)

## Installation

Extract the ZIP to any folder and open `Guyrapu.exe`. You do not need to install anything or have administrator permissions.

You need Windows 10 or 11, an internet connection and at least one Windows voice, which is added in *Settings, Time & language, Speech*. ElevenLabs is optional and requires your own account.

## The main window

When you open Guyrapu, the focus is in the *Link or ID* field. Paste the link of a live stream or a video and press *Connect*. The *Recent items* list offers the live streams you have already opened.

The window has three regions: *Connection*, *Content* and *Player*. In *Content* are the *Live chat*, *Comments* and *Information* tabs. Every change of region or tab is announced.

| Key in the Recent items list | Action |
|---|---|
| `Enter` | Open the live stream |
| `Delete` | Remove it from the history |

## The chat

Each message is read with the chosen voice and has a sound according to who writes (channel owner, moderator, verified account or member) and according to what it is (Super Chat, membership or TikTok gift).

In the chat list, the arrows move from one message to another, and when you type a few letters the focus jumps to the first author that starts that way. The context menu copies the message, mutes the author for the session and assigns an alias. With the Google session started, it also puts the author in timeout or hides them from the channel.

On TikTok, Guyrapu only reads: TikTok does not offer an official way to comment or moderate.

With a Restream profile that reads the YouTube chat and the TikTok chat, both arrive in the same list and each row says which platform it is from. In *Preferences*, on the *Live events* category, *Each platform's own sound* chooses whether TikTok messages always have their sound, only with several chats or never, and *Announce which platform each message has when there are multiple chats* makes the voice say it too.

### Live events

Joins, likes, followers, gifts, polls, goals and TikTok battles are configured in *Preferences*, on the *Live events* category. Each event has a list with these modes:

- *Main voice and sound* and *Secondary voice and sound*: it appears in the list, plays a sound and is read with that voice.
- *Main voice without sound* and *Secondary voice without sound*: it appears and is read with that voice, without its sound.
- *Sound only*: it appears and plays a sound, without being read.
- *List only*: it appears without sound and without being read.
- *Off*: it does not appear.

*Group joins* and *Group likes* bring together in one row what arrives in a few seconds, such as “Ana, Beto and Caro joined”.

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

On a published video, the *Comments* tab reads the comments, and with the Google session it lets you comment and reply.

## Voices and sounds

Guyrapu reads with three voice engines: SAPI 5 and OneCore, which come with Windows, and ElevenLabs, which requires an account. The engine, the voice, the speed, the volume and the pitch are chosen in *Preferences*, on the *Voices* category, where *Test voice* plays a sample. If ElevenLabs fails because of the network or a lack of balance, Guyrapu reads with the *Backup Windows voice* and warns you once.

Each type of message, event and notice has its sound. In the *Sounds* category you choose the theme, *Default* or *Soft*, and turn off each sound separately. To create your own theme, copy the `sounds/themes/default` folder with another name and replace the `.wav` files.

## Player

The live stream video plays inside Guyrapu, with the commands in the *Player* menu. In a live stream, each jump says the distance to the live stream, for example “40 seconds behind the live stream”, and on YouTube you can go back up to an hour. If the connection fails, Guyrapu reconnects at the same point.

*Play sound only, without the picture*, in *Preferences*, on the *Player* category, is checked: without the picture, jumps are almost immediate.

## Music

Guyrapu plays music while you stream. It uses the Music folder next to the application, or the one you choose in *Preferences*, on the *Music* category. The commands are in the *Music* menu, and *Choose music…* opens the *Music* window:

- *Collections* shows the *Library*, which is your folder, and your playlists.
- *Find* filters while you type, also without accents.
- *Songs* has a context menu to play now, next or to the end, and to add to the queue or to a playlist.
- *Show the queue* shows what is going to play.
- *Open link…* adds a YouTube video or playlist to the queue.

When you create or edit a playlist, a dialog with two lists opens. In *Playlist songs*, `Delete` removes the song and `Alt+Up Arrow` and `Alt+Down Arrow` move it. *All songs* shows the folder with a checkbox for each song, checked for the ones already in the playlist: checking or unchecking it adds or removes the song. In both, `Enter` plays the song.

*Match song volume* makes them all sound at a similar volume. Each file is measured once, with the *Match the volume* button in the *Music* window, and it is not modified. Between one song and the next there is a crossfade, which is adjusted in *Crossfade between songs, in seconds*.

With *Use music shortcuts in any application*, the music shortcuts also work in OBS or in a game, and those keys stop reaching the other applications.

Where NVDA detects a table, as in File Explorer, it keeps Ctrl+Alt and the arrows. In that case, press NVDA+F2 before the shortcut.

## Going live

Guyrapu starts and ends the live stream with OBS Studio, to YouTube or to several platforms at once with Restream.

### Before going live for the first time

- Turn on the OBS WebSocket server in *Preferences*, on the *OBS* category.
- For YouTube, start the Google session and enable live streams on your channel.
- For Restream, connect the account and create a profile. See [Restream](#restream).
- So that OBS uses a different profile when broadcasting horizontally, vertically or recording, assign them on the *Profiles* tab of the *OBS panel*. See [OBS profiles](#obs-profiles).

If OBS is closed, Guyrapu opens it in the notification area.

### Starting the live stream

1. Press *Broadcast live*, next to *Connect*. The *Broadcast to* dialog opens, with the destination from last time already chosen.
2. Choose *YouTube* or a Restream profile and press *Continue*.
3. Guyrapu prepares OBS and checks the scene: whether it is empty, whether an
   image comes out black or whether the microphone is muted. If it finds a
   problem, the button chosen by default is *Cancel*. If you broadcast to
   TikTok and the Restream account is also going to send the live stream to
   other enabled destinations, the confirmation before starting says so, with
   its own sound and the focus on *Cancel*, and suggests choosing a Restream
   profile. If something fails when starting, the error always appears in a
   box.
4. For YouTube, or a profile with YouTube, type the title, the description and the privacy. The rest of the data is optional, and Guyrapu remembers the last thing you typed. To do tests, use *Unlisted*.
5. When the live stream starts, Guyrapu connects the chat and announces it.

If the internet connection is lost, YouTube waits for it to come back without ending the live stream. Closing Guyrapu does not interrupt the live stream, and when you open it again it recognizes it.

During the live stream, the button is called *End live stream* and asks for confirmation, with *Keep broadcasting* chosen by default. When it ends, Guyrapu says how many frames were dropped, whether it was due to the network, the encoder or the drawing of the scene, and what to change in the profile for the next one. OBS goes back to the profile it had before the live stream, also if you cancel it before it starts.

### Microphone

*Mute OBS microphone*, in the *OBS* menu, mutes or turns on the microphone. When you turn it on, Guyrapu says which device it uses and warns if no sound comes in. To set the device, use *Choose a device…* on the *Audio* tab of the *OBS panel*.

### Recording and saving clips

With *Record while broadcasting* checked, in the *Broadcast* menu, OBS records for as long as the live stream lasts. If the recording cannot start, the live stream continues and a warning plays. To record without broadcasting, use the *OBS* menu or the *Recording* tab of the *OBS panel*.

*Save clip* saves the last 30 or 60 seconds, according to the *Clips* list in *Preferences*, on the *OBS* category. With *Allow !clip in chat*, anyone in the chat saves a clip by typing `!clip`, with a wait between clips that is chosen in the same category.

When you stop a recording or save a clip, Guyrapu says the file name.

### Chat on video

The chat on video shows the messages and gifts over the live stream image, for the viewers, with a color for each person. It is added with *Add source…*, *Chat on video…*, on the *Scene* tab of the *OBS panel*. In another streaming application, such as Streamlabs, it is added as a browser source with this link:

    http://127.0.0.1:8730/chat

## OBS panel

The *OBS panel* brings together in tabs what is done with OBS, and it is opened from the *OBS* menu. If OBS is closed, the panel opens it. Everything can still be done in OBS, and the OBS plugin for NVDA still works.

### General

*Status* summarizes the broadcast, the recording, the current scene, the microphone and the computer usage. *Show OBS* brings the OBS window to the front, also from the notification area. *Close OBS*, also in the *OBS* menu, closes OBS without forcing it, so it does not ask about safe mode when you open it again. If OBS is broadcasting or recording, it does not close it and warns.

*Test computer…* records for a few seconds with the profile in use to see whether the PC drops frames. If it does, it tries lighter settings until it finds some that work and offers to save them in the profile. With the Aitum Vertical Canvas plugin in OBS, the dialog offers to include the vertical canvas, to know whether the PC can broadcast in both orientations at the same time. Test recordings are deleted at the end.

*Test connection…* does a private test live stream on YouTube, which nobody sees and which deletes itself, to know what bitrate your connection supports, and offers to save it in the profile. It needs the Google session.

The computer and connection tests show their progress in a window, with a wait sound, and if they fail they leave the error written in it. In the connection test, if an attempt fails with an OBS error, Guyrapu tries again and continues with the next one. If the YouTube session expired, it says so and explains how to start it again.

### Scene

The *Scenes* list shows each scene, whether it is the current one and how many sources it has. Browsing it does not change what is broadcast: *Change scene* puts the chosen scene on air, and *Add scene…* creates a new one.

*Create vertical version*, in the context menu of a scene, creates a copy with the same name followed by “vertical”, with the same sources and a vertical layout. When broadcasting vertically, that copy goes on air, and at the end the scene that was there comes back.

The *Sources* list shows the sources of the chosen scene, and each row says where the source is, what part of the video it occupies and whether it is visible. The context menu of each row brings together its actions. *Size and position…* places it in one of nine positions, with a size from one fifth to the full width of the video, and *Move with arrows* moves it in steps. If the scene has no sources, the list says so and explains how to add one.

*Add source…* adds to the scene a camera, a window, game or screen capture, an image, a media file, a text, the chat on video or a source from another scene.

*Apply layout…* distributes the whole scene at once. It comes with three
factory layouts, *Full screen*, *Picture-in-picture* and *Split in two*, and
the dialog lets you choose which source goes in each place, the corner, the
split and the chat. *Fit* decides what happens if the aspect ratio does not
match: *Fit* shows the whole source, *Fill* crops the edges and *Automatic*
fills with the camera and fits the rest. *Save as…* saves your own layout.
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
- *Prepare profiles…* creates a profile for broadcasting horizontally, another one vertically and another one for recording, checks which settings work well on your PC, assigns them and says what it did. The profiles you already had do not change. It shows its progress in a window, with a wait sound, and if it fails it leaves the error written in it.

When broadcasting or recording without a live stream, Guyrapu switches OBS to the assigned profile, and at the end it goes back to the one it had.

With no profiles, the list says how to create one. *New…* creates the profile and opens its settings. In the list, `Delete` removes the profile, `Enter` opens its settings and the Applications key opens a menu with the same actions as the buttons.

### Broadcast

*Broadcast live* opens the *Broadcast to* dialog, the same as the button in the main window, and *Restream…* opens the Restream window.

### Audio

The *Audio sources* list shows each source with its status and its filters. If there are no audio sources, the list says so. The buttons act on the chosen source:

- *Mute* mutes or turns it on.
- *Test level* says every five seconds whether the level is right, low or high, or whether it is clipping, until you press *Stop test*.
- *Filters…* turns on noise suppression, the noise gate and gain. If OBS already had one of those filters, that one is used.
- *Listen* lets you hear the source with its filters through the OBS monitoring device. Use headphones to avoid feedback.
- *Choose a device…* sets the microphone device.

### Recording

*Start recording* and *Stop recording* record without broadcasting, and *Pause recording* pauses the recording in progress. The *Recordings and clips* list brings together the recordings and the clips, from newest to oldest. Its context menu opens the file or its folder, copies the path or removes it from the list without deleting the file. If OBS converts the recording to MP4 at the end, the list shows the MP4.

## Restream

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

*Show* chooses between upcoming events, those that are live and the history. *Event detail* shows its status, its times, its destinations and the description. The context menu copies the event links or information, opens the live stream and adds the statistics to the detail. If there are no events for the chosen filter, the list says so.

### Warnings during the live stream

With a Restream profile, Guyrapu warns with its own sound when Restream stops receiving the OBS signal and when it recovers it, when the signal is weak and when a destination disconnects or comes back.

## Camera framing

If the current scene has a camera, Guyrapu says how it sees you: how many faces there are, whether you are centered, far away, sideways or outside the edge, whether light is missing or there is backlight, and whether the image froze. Left and right are said as the movement you have to make: “Move to your left.”. The image is analyzed on the computer and is not sent anywhere.

The commands are in the *OBS* menu:

- *Announce camera framing* says the framing. Twice in a row, it starts the guide with beeps, which sound from the side you have to move to, higher for up and lower for down. In the center a confirmation sounds.
- *Warn when the face leaves the frame* warns with a sound when the face leaves and with another when it comes back.
- *Show or hide the camera* hides the camera from the scene without turning off the device.

In *Preferences*, on the *Camera* category, you choose the OBS camera, the guide sound and whether left and right are inverted.

## Scheduled messages

Scheduled messages are sent to the chat every so often, for example your social networks every ten minutes. They are configured in *Preferences*, on the *Scheduled messages* category, and they work on your own YouTube live stream with the Google session started. YouTube usually blocks links: type the user name instead. If YouTube returns an error, the messages stop and Guyrapu warns you once.

## Downloads and history

The *Download manager* downloads videos, audio or YouTube playlists in MP4, WebM, MP3 or M4A, two at a time. What is downloaded goes to the Downloads folder, next to the application. On the *Search on YouTube* tab, Space plays a result in the music without downloading it. If downloads fail, use *Update yt-dlp*, in the *Tools* menu.

The *Live stream history* shows what you watched, with a tab for YouTube and another for TikTok.

## Spoken status

*Announce status*, in the *View* menu, summarizes the connection, the live stream, the viewers, the messages read and the donations. What is included is chosen in *Preferences*, on the *Status (F2)* category. Twice in a row, it opens the *Session status* window, with each piece of data on one line.

## Asking the AI

An artificial intelligence looks at an OBS screenshot and says what it sees, for example whether a source comes out black. It requires OBS open and a provider key.

In *Preferences*, on the *Artificial intelligence* category, you choose the provider, such as Google Gemini, OpenAI, Anthropic or OpenRouter, save the key and choose the model. The key is kept in the Windows Credential Manager. If the key does not have the format Guyrapu expects, it warns you and offers to use it anyway, in case the provider changed the format.

*Ask the AI about the picture…*, in the *View* menu, opens a window where *Add screenshot* chooses the scene or a source, and the question is typed in *Message*. *Quick query* sends the current scene and reads the response without opening any window.

The screenshot and what you type are sent to the provider, and the first send asks for confirmation. A black screenshot, such as the one left by the NVDA screen curtain, is not sent. In that case, change the capture method of that source to Windows 10 in OBS.

## Google session

The Google session lets you moderate, write in the chat, comment on videos and create the YouTube live stream. Without it, everything else works.

To start it, open *Preferences*, on the *YouTube* category, press *Sign in* and authorize in the browser. The YouTube and Restream sessions are saved encrypted with your Windows account: if you copy the application folder to another computer, you will have to start them again. YouTube's daily quota is shared among those who use Guyrapu. To have your own, see the [API setup guide](../CONFIGURACION_API.md).

## Preferences

*Preferences…*, in the *Tools* menu, brings together the configuration by categories, and the changes are applied when you press *Save*. In *General* you choose the language and the update channel, and you export, import or reset the preferences. *Show important notices also in a message box* also shows the result of what you do in a box. Each category is prepared the first time you choose it, so the window opens faster.

Preferences are saved in `config.ini` and `sounds.ini`, in the `data` folder next to the application.

### Changing a shortcut

In the *Shortcuts* category, each action has a button with its shortcut. Press the button and then the new combination. If the combination is already in use or does not belong to that family, Guyrapu says why and keeps waiting. *Reset shortcuts to factory defaults* returns to the original shortcuts.

| Key when changing a shortcut | Action |
|---|---|
| `Enter` | Leave the action without a shortcut |
| `Esc` | Cancel |

## Keyboard shortcuts

Each family of shortcuts uses its own modifier keys. They all also appear in the menu bar, next to their command. In action lists, typing the first letters jumps to the item that starts that way, and a sound plays when you reach the beginning or the end.

### Fixed

| Shortcut | Action |
|---|---|
| `F1` | Open the manual |
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

### Windows (Ctrl+Shift)

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+P` | Preferences |
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
| `Ctrl+F2` | Describe the OBS scene |
| `Ctrl+Shift+F2` | Quick query |
| `Ctrl+F3` | Announce camera framing. Twice, guide with beeps |
| `Ctrl+Shift+F3` | Warn when the face leaves the frame |
| `Alt+F3` | Show or hide the camera |

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

### Recent chat messages (Ctrl+Shift and a number)

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+1` | Read the last message |
| `Ctrl+Shift+2` to `Ctrl+Shift+9` | Read from the second to the ninth from the end |
| `Ctrl+Shift+0` | Read the tenth from the end |

With *Read recent messages in any application*, in *Preferences*, on the *Reading* category, these shortcuts also work with another application in the foreground. If another application already uses one of these combinations, a tone sounds and Guyrapu says which one.

## Updating

*Check for updates…*, in the *Help* menu, says whether there is a new version, shows what is new and installs it. Guyrapu closes and opens again in about a minute, and keeps the `data` folder, the downloads and your own sounds. If the new version does not open, it goes back to the previous one on its own. *Update channel*, in *Preferences*, on the *General* category, chooses whether only stable versions are offered or beta versions too.

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
