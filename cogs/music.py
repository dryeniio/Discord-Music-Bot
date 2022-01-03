import pprint
import asyncio
import random
import math

import nextcord
from nextcord import voice_client
from nextcord import player
from nextcord import user
from nextcord.channel import VoiceChannel
from nextcord.embeds import Embed
from nextcord.ext import commands

from youtube_dl import YoutubeDL
import re

import json
with open("config.json", encoding="utf-8") as config:
    config = json.load(config)

URL_REG = re.compile(r'https?://(?:www\.)?.+')
YOUTUBE_VIDEO_REG = re.compile(
    r"(https?://)?(www\.)?youtube\.(com|nl)/watch\?v=([-\w]+)")


class music(commands.Cog):
    def __init__(self, client):
        self.client = client

        set_volume = 0.5
        self.set_volume = set_volume

        # all the music related stuff
        self.is_playing = False
        self.event = asyncio.Event()

        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {
            'username': config['username'],
            'password': config['password'],
            'cookiefile': './cookies.txt',
            'format': 'bestaudio/best',
            'restrictfilenames': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            # 'default_search': 'auto',
            'extract_flat': True
        }
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

        self.vc = ""

     # searching the item on youtube
    def search_yt(self, item):

        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                if (yt_url := YOUTUBE_VIDEO_REG.match(item)):
                    item = yt_url.group()
                elif not URL_REG.match(item):
                    item = f"ytsearch:{item}"
                info = ydl.extract_info(item, download=False)
            except Exception:
                return False

        try:
            entries = info["entries"]
        except KeyError:
            entries = [info]

        if info["extractor_key"] == "YoutubeSearch":

            entries = entries[:1]

        tracks = []

        for t in entries:

            tracks.append(
                {'source': f'https://www.youtube.com/watch?v={t["id"]}', 'title': t['title'], 'url': t['url'], 'info': ['description'], 'duration': t['duration'], 'channel': t['uploader']})

        # if search:
        #    tracks = {'source': info['formats'][0]['url'], 'title': info['title']}

        return tracks

    # infinite loop checking
    async def play_music(self):

        self.event.clear()

        if len(self.music_queue) > 0:

            self.is_playing = True

            m_url = self.music_queue[0][0]['source']

            # If source was a stream (not downloaded), so we should regather to prevent stream expiration
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(m_url, download=False)
                    m_url = info['formats'][0]['url']
                    self.current = self.music_queue[0]
                except Exception:
                    return False

            # try to connect to voice channel if you are not already connected

            if self.vc == "" or not self.vc.is_connected() or self.vc == None:
                self.vc = await self.music_queue[0][1].connect()
            else:
                await self.vc.move_to(self.music_queue[0][1])

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)

            self.vc.play(nextcord.PCMVolumeTransformer(nextcord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), volume=self.set_volume),
                         after=lambda l: self.client.loop.call_soon_threadsafe(self.event.set))
            await self.event.wait()
            await self.play_music()
        else:
            self.is_playing = False
            self.music_queue.clear()
            await self.vc.disconnect()

    def shuffle(self):
        random.shuffle(self.music_queue)

    @commands.command(name="help", alisases=['ajuda'], help="Comando de ajuda.")
    async def help(self, ctx):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Ajuda (help)"))  # console-log

        helptxt = ''
        for command in self.client.commands:
            helptxt += f'm!**{command}** - {command.help}\n'
        embedhelp = nextcord.Embed(
            colour=1646116,  # grey
            title=f'Comandos do {self.client.user.name}',
            description=helptxt + \
            '\n[Entre no nosso Discord!](https://jonetoju.tk)'
        )
        embedhelp.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.send(embed=embedhelp)

    @commands.command(name="p", help="Toca uma música do YouTube.", aliases=['tocar', 'r', 'reproduzir', 't', 'play'])
    async def p(self, ctx: commands.Context, *, query: str = "Matheus Fernandes e Dilsinho - Baby Me Atende (Clipe Oficial)"):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Play de música"))  # console-log

        """Reproduza uma música ou playlist.
        Parametros
        ------------
        play: Reproduz uma música qualquer [Link ou Texto]
            Só é aceito apenas links e músicas do youtube.
        """

        try:
            voice_channel = ctx.author.voice.channel
        except:
            # if voice_channel is None:
            # you need to be connected so that the bot knows where to go
            embedvc = nextcord.Embed(
                colour=1646116,  # grey
                description='Para tocar uma música, primeiro se conecte a um canal de voz.'
            )
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Autor não conectado a um canal."))  # console-log
            await ctx.reply(embed=embedvc)
            return
        else:
            songs = self.search_yt(query)
            if type(songs) == type(True):
                embedvc = nextcord.Embed(
                    colour=12255232,  # red
                    description='Algo deu errado! Tente mudar ou configurar a playlist/vídeo ou escrever o nome dele novamente!'
                )
                print("Status: {} Código do erro: {}".format(
                    "Erro de solicitação!", "ERRO DESCONHECIDO!"))  # console-log
                await ctx.reply(embed=embedvc)
            else:

                if (size := len(songs)) > 1:

                    txt = f"Você adicionou **{size} músicas** na fila!"
                    print("Foram adicionadas {} novas músicas!".format(size))
                    print("Status: {}, {}".format(
                        "Concluido com sucesso!", "Playlist recebida."))  # console-log

                else:
                    # text-link
                    txt = f"[**{songs[0]['title']}**]({songs[0]['source']})"
                    print("Status: {}, {}".format(
                        "Concluido com sucesso!", "Música recebida."))  # console-log

                # url
                url_video = f"{songs[0]['source']}"
                # thumbnail
                thumb_url = f"https://img.youtube.com/vi/{url_video[32:43]}/hqdefault.jpg"

                print('Reproduzindo o Vídeo:', url_video)  # console-log
                print('Com thumbnail:', thumb_url)  # console-log

                duration = songs[0]['duration']
                m1, s1 = divmod(int(duration), 60)
                duration = f"{m1} minutos e {s1} segundos."

                embedvc = nextcord.Embed(
                    title="**Você adicionou:**",
                    colour=32768,  # green
                    description=f"\n\n{txt}\n\n"
                )
                if not (size := len(songs)) > 1:
                    embedvc.add_field(
                        name="**Canal:**",
                        value=songs[0]['channel'],
                        inline=True
                    )
                    embedvc.add_field(
                        name="**Duração:**",
                        value=duration,
                        inline=True
                    )
                embedvc.set_footer(text="Boa Música!")
                embedvc.set_thumbnail(url=thumb_url)
                await ctx.reply(embed=embedvc)

                for song in songs:
                    self.music_queue.append([song, voice_channel])

                if self.is_playing == False:
                    await self.play_music()

    @commands.command(name="fila", help="Mostra as atuais músicas da fila.", aliases=['q', 'f', 'queue'])
    async def q(self, ctx):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Fila do Player"))  # console-log

        """Mostra a fila de reprodução atual.
        Parametros
        ------------
        fila: Mostra a fila de reprodução.
        """

        retval = ""
        for i in range(0, len(self.music_queue)):
            retval += f'**{i+1} - **' + self.music_queue[i][0]['title'] + "\n"

        if retval != "":
            embedvc = nextcord.Embed(
                colour=12255232,
                description=f"{retval}"
            )
            print("Status: {}, {}".format(
                "Concluido com sucesso!", "Fila mostrada!"))  # console-log
            print(retval)
            await ctx.send(embed=embedvc)
        else:
            embedvc = nextcord.Embed(
                colour=1646116,
                description='Não existe músicas na fila no momento.'
            )
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Sem fila!"))  # console-log
            await ctx.send(embed=embedvc)

    @commands.command(name="pular", help="Pula a atual música que está tocando.", aliases=['skip', 's'])
    async def skip(self, ctx):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Palar a música."))  # console-log

        """Pula para a próxima faixa da fila de reprodução.
        Parametros
        ------------
        pular: Troca para a próxima faixa.
        """

        if self.vc != "" and self.vc:
            self.vc.stop()
            embedvc = nextcord.Embed(
                colour=1646116,  # ggrey
                description=f"Você pulou a música."
            )
            await ctx.message.add_reaction('✅')
            await ctx.send(embed=embedvc)
            print("Status: {}, {}".format(
                "Concluido com sucesso!", "Música pulada."))  # console-log

    @skip.error  # Erros para kick
    async def skip_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embedvc = nextcord.Embed(
                colour=12255232,
                description=f"Você precisa da permissão **Gerenciar canais** para pular músicas."
            )
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Permição insuficiente do requerente."))  # console-log
            await ctx.send(embed=embedvc)
        else:
            raise error

    @commands.command(name="parar", help="Para o player de tocar músicas.", aliases=["stop", "sair", "leave", "l"])
    async def stop(self, ctx: commands.Context):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Parar player"))  # console-log

        """Para o player e a reprodução atual, limpa a fila de reprodução e desconecta o bot do canal.
        Parametros
        ------------
        parar: Para o player e limpa a fila de reprodução.
        """

        embedvc = nextcord.Embed(colour=12255232)

        if not ctx.me.voice:
            embedvc.description = "Não estou conectado em um canal de voz."
            await ctx.reply(embed=embedvc)
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Player não conectado."))  # console-log
            return

        if not ctx.author.voice or ctx.author.voice.channel != ctx.me.voice.channel:
            embedvc.description = "Você precisa estar no meu canal de voz atual para usar esse comando."
            await ctx.reply(embed=embedvc)
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Autor não coonectado."))  # console-log
            return

        if any(m for m in ctx.me.voice.channel.members if not m.bot and m.guild_permissions.manage_channels) and not ctx.author.guild_permissions.manage_channels:
            embedvc.description = "No momento você não tem permissão para usar esse comando."
            await ctx.reply(embed=embedvc)
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Permição insuficiente do requerente."))  # console-log
            return

        self.is_playing = False
        self.music_queue.clear()
        await self.vc.disconnect(force=True)

        embedvc.colour = 1646116
        embedvc.description = "Você parou o player"
        print("Status: {}, {}".format(
            "Concluido com sucesso!", "Player PARADO!"))  # console-log
        await ctx.reply(embed=embedvc)

    @commands.command(name="pause", help="Pausa e continua uma música.", aliases=["resume"])
    async def pause(self, ctx):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Clear Queue"))  # console-log

        paused = ctx.voice_client.is_paused()

        if paused != True:
            print("Status: {}, {}".format(
                "Concluido com sucesso!", "Player pausado!"))  # console-log
            ctx.voice_client.pause()
            txt = f"pausou"
            embedvc = nextcord.Embed(
                color=12255232,  # Red
                description=f"Você {txt} a música!"
            )
            await ctx.message.add_reaction('✅')

        else:
            if paused != False:
                print("Status: {}, {}".format("Concluido com sucesso!",
                      "Player retomado!"))  # console-log
                ctx.voice_client.resume()
                txt = f"continuou"
                embedvc = nextcord.Embed(
                    colour=32768,  # green
                    description=f"Você {txt} a música!"
                )
                await ctx.message.add_reaction('✅')

            else:
                print("Status: {} Código do erro: {}".format(
                    "Erro de solicitação!", "ERRO DESCONHECIDO!"))  # console-log
                embedvc = nextcord.Embed(
                    color=12255232,  # Red
                    description=f"Ocorreu um erro!"
                )

        await ctx.send(embed=embedvc)

    @commands.command(name="clear", help="Limpa a fila de músicas.", aliases=["limpar"])
    async def clear(self, ctx):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Clear Queue"))  # console-log

        fila = ""
        for i in range(0, len(self.music_queue)):
            fila += f"{i}"

        if fila != "":

            self.music_queue.clear()
            print("Status: {}, {}".format(
                "Concluido com sucesso!", "Playlist limpa!"))  # console-log
            embedvc = nextcord.Embed(
                color=12255232,  # red
                description=f"Você limpou a fila!"
            )

        else:
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Sem fila!"))  # console-log
            embedvc = nextcord.Embed(
                color=1646116,  # gray
                description=f"Não existe fila no momento!"
            )

        await ctx.reply(embed=embedvc)

    @commands.command(name="shuffle", help="Deixa a playlist como aleatória.", aliases=["surfar", "aleatorio", "embaralhar", "destino"])
    async def _shuffle(self, ctx: commands.Context):

        print("O player {}, usou o comando: {}.".format(
            ctx.author, "Shuffle"))  # console-log

        #"""Embaralha a playlist."""

        if len(self.music_queue) == 0:
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Sem fila!"))  # console-log

            embedvc = nextcord.Embed(
                color=1646116,  # gray
                description=f"Não existe fila no momento!"
            )
            return await ctx.send(embed=embedvc)

        random.shuffle(self.music_queue)
        await ctx.message.add_reaction('✅')
        embedvc = nextcord.Embed(
            color=32768,  # green
            description=f"Você embaralhou a playlist."
        )
        print("Status: {}, {}".format("Concluido com sucesso!",
              "Playlist embaralhada!"))  # console-log
        await ctx.send(embed=embedvc)

    @commands.command(name='volume', aliases=['vol', 'v'], description="changes Kermit's volume", help="Altera o volume do player.")
    async def change_volume(self, ctx, *, vol: float = None):

        print("O player {}, usou o comando: {}".format(
            ctx.author, "Volume"))  # console-log

        """Troque o Volume do Bot #BETA #QUEBRADA
        Parametros
        ------------
        volume [Exibe o volume atual]
        volume: real ou flutuante [Obrigatório]
            O volume para definir o player em porcentagem. Deve estar entre 1 e 100.
        """

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Sem música!"))  # console-log
            embedvc = nextcord.Embed(title="",
                                     description="Não existe música sendo reproduzida!",
                                     color=1646116,  # gray
                                     )
            await ctx.message.add_reaction('❌')
            return await ctx.send(embed=embedvc)

        if not vol:
            embedvc = nextcord.Embed(
                title="",
                description=f"🔊 **{(ctx.voice_client.source.volume)*100}%**",
            )
            print("Status: {}, {} {}%".format("Concluido com sucesso!",
                  "Mostrou o volume atual:", ctx.voice_client.source.volume*100))  # console-log
            return await ctx.send(embed=embedvc)

        if not 0 < vol < 101:
            embedvc = nextcord.Embed(title="",
                                     description="Selecione um valor entre 0 e 100!",
                                     color=1646116,  # gray
                                     )
            await ctx.message.add_reaction('❌')
            return await ctx.send(embed=embedvc)

        player = self.vc

        source_vc = ctx.voice_client.source

        if source_vc:
            source_vc.volume = vol / 100

        set_volume = float(source_vc.volume)

        self.set_volume = set_volume
        player.volume = set_volume
        embedvc = nextcord.Embed(
            title="", description=f'**`{ctx.author}`** volume definido para: **{vol}%**', color=nextcord.Color.green())
        print("Status: {}, volume alterado para: {}%".format(
            "Concluido com sucesso!", ctx.voice_client.source.volume*100))  # console-log
        await ctx.send(embed=embedvc)

    @commands.command(name="nowplaying", help="Mostra a música reproduzindo atualmente.", aliases=["musica", "reproduzindo", "np"])
    async def _np(self, ctx):

        print("O player {}, usou o comando: {}".format(
            ctx.author, "Now Playing"))  # console-log

        retval = ""

        if self.is_playing == False:
            print("Status: {} Código do erro: {}".format(
                "Erro de solicitação!", "Sem música!"))  # console-log
            embedvc = nextcord.Embed(title="",
                                     description="Não existe música sendo reproduzida!",
                                     color=1646116,  # gray
                                     )
            await ctx.message.add_reaction('❌')
            return await ctx.send(embed=embedvc)

        if len(self.music_queue) >= 0:
            print("Status: {}".format("Concluido com sucesso!"))  # console-log

            retval += self.current[0]['title'] + "\n"
            # url
            url_video = f"{self.current[0]['source']}"
            # thumbnail
            thumb_url = f"https://img.youtube.com/vi/{url_video[32:43]}/hqdefault.jpg"

            duration = self.current[0]['duration']
            m1, s1 = divmod(int(duration), 60)
            duration = f"{m1} minutos e {s1} segundos."

            txt = f"[{retval}]({url_video})"

            channel = self.current[0]['channel']

        embedvc = nextcord.Embed(
            title="**Reproduzindo:**",
            colour=32768,  # green
            description=f"\n\n{txt}\n\n"
        )
        embedvc.add_field(
            name="**Canal:**",
            value=channel,
            inline=True
        )
        embedvc.add_field(
            name="**Duração:**",
            value=duration,
            inline=True
        )
        embedvc.set_footer(text="Boa Música!")
        embedvc.set_thumbnail(url=thumb_url)
        await ctx.send(embed=embedvc)


def setup(client):
    client.add_cog(music(client))
