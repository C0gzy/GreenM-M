
import urllib
import re
import asyncio
import datetime
import yt_dlp
import discord
import os
import imdb
from discord.ext import commands
from discord.utils import get
import concurrent.futures

################################# Variables ################################################################################



token =  os.getenv("Token")
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='?',intents=intents)


mode = 0

Functionality = {
    "Main" : [],
    "Version" : "1.1",
    "Modes" : [" Patched Download Speeds"],
    "Voice" : [],
    "Queue" : {
            "Songs" : [],
            "Name" : [],
            "Thumbnail" : [],
            "Duration" : []
        },
    "VoiceChannel" : None,
    "PlayingSong" : False,
    "NumberTrack" : 0
}

'''
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
'''

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': None,
    'forceip':'4',
    'extractaudio': True,
    'rm-cache-dir' : True  

}


################################# Bot commands ################################################################################
@bot.event
async def on_ready(): 
    print("Bot ready for operation")
    synced = await bot.tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(Functionality["Version"] + Functionality["Modes"][mode]))

@bot.tree.command(name="play", description="Use this to play youtube videos")
async def play(interaction: discord.Interaction , search: str , lowqualitymode:bool= None):
    await interaction.response.send_message(content="Searching ...")
    if lowqualitymode == None or lowqualitymode == False:
        ydl_opts["format"] = "bestaudio/best"
    else:
        ydl_opts["format"] = "worstaudio/worst"

    VC = await JoinVoiceChannel(interaction) 
    if VC == False:
        await interaction.response.send_message("Not in voice channel please join one and try again")
        return
    YoutubeVideo = Search_Youtube(search)
    voice = get(bot.voice_clients, guild=interaction.guild)
    if Functionality["PlayingSong"] == True:
        await interaction.edit_original_response(content="Song already playing adding to Queue ...")
        await DownloadSong(YoutubeVideo)
        await interaction.edit_original_response(content="Added song 🎵" + Functionality["Queue"]["Name"][len(Functionality["Queue"]["Name"]) - 1]  + "🎵 to the queue In position "+ str(len(Functionality["Queue"]["Name"]) - 1))
        return
    else:
        await interaction.edit_original_response(content="Downloading ...")
        Functionality["PlayingSong"] = True
        await DownloadSong(YoutubeVideo)
        print(Functionality["Queue"]["Songs"][0])
        playsong(voice,interaction)
        await interaction.edit_original_response(content="Now Playing 🎵"+ Functionality["Queue"]["Name"][0] +"🎵")
       
    
@bot.tree.command(name="skip", description="Skip current song")#,pass_context=True,)
async def skip(interaction: discord.Interaction):#ctx):
    voice = get(bot.voice_clients, guild=interaction.guild)
    if voice and voice.is_playing():
        print("Playing Next Song")
        discord.VoiceClient.stop(voice)
        #voice.stop()
        await interaction.response.send_message(content="Next Song")
    else:
        print("No music playing")
        await interaction.response.send_message(content="No music playing failed")


@bot.tree.command(name="whatsplaying", description="shows current song playing")#,pass_context=True,)
async def whatsplaying(interaction: discord.Interaction):#ctx):
    if (Functionality["PlayingSong"] == False):
        await interaction.response.send_message(content="No song Playing")
        return
    
    embedVar = discord.Embed(title=Functionality["Queue"]["Name"][0] ,color=0x008200)
    embedVar.add_field(name="Length: ", value=datetime.timedelta(seconds=Functionality["Queue"]["Duration"][0]), inline=False)
    embedVar.set_image(url=Functionality["Queue"]["Thumbnail"][0])
    await interaction.response.send_message(embed=embedVar)

@bot.tree.command(name="queue", description="Shows whats in the queue")
async def queue(interaction: discord.Interaction):
    if (len(Functionality["Queue"]["Name"]) > 0):
        embedVar = discord.Embed(title="Current Queue:" ,color=0x008200)

        for i in range(len(Functionality["Queue"]["Name"])):
            embedVar.add_field(name="Position "+str(i)+": ", value=Functionality["Queue"]["Name"][i], inline=False)

        await interaction.response.send_message(embed=embedVar)
    else:
        await interaction.response.send_message(content="Queue is empty")


@bot.tree.command(name="leave", description="Stops playing music and leaves")
async def leave(interaction: discord.Interaction):
    voice = get(bot.voice_clients, guild=interaction.guild)
    discord.VoiceClient.stop(voice)
    await voice.disconnect()

    Functionality["PlayingSong"] = False
    Functionality["Queue"]["Songs"] = []
    Functionality["Queue"]["Thumbnail"] = []
    Functionality["Queue"]["Name"] = []
    Functionality["Queue"]["Duration"] = []
    Functionality["NumberTrack"] = 0
    await interaction.response.send_message(content="Left Call")

@bot.tree.command(name="debug" ,description="Will display variable infomation for debugging")
async def debug(interaction: discord.Interaction):
    try:
        embedVar = discord.Embed(title="Green M&M Debug" ,color=0x008200)
        embedVar.add_field(name="PlayingSong : ", value=Functionality["PlayingSong"], inline=False)
        embedVar.add_field(name="Queue Songs : ", value= ' / '.join(Functionality["Queue"]["Songs"]), inline=False)
        embedVar.add_field(name="Queue Thumbnails : ", value=  ' / '.join(Functionality["Queue"]["Thumbnail"]), inline=False)
        embedVar.add_field(name="Queue Names : ", value=  ' / '.join(Functionality["Queue"]["Name"]), inline=False)
        embedVar.add_field(name="Queue Durations : ", value=  ' / '.join(Functionality["Queue"]["Duration"]), inline=False)
        embedVar.add_field(name="NumberTrack : ", value=Functionality["NumberTrack"], inline=False)

        await interaction.response.send_message(embed=embedVar)
    except Exception as error:
        await interaction.response.send_message(content=error)

#Add volume settings

############################################ Other Commands ######################################################################

@bot.tree.command(name="movienight", description="Creates a post about movie night",)
async def movienight(interaction: discord.Interaction, movie:str , timestart:str = None):
    await interaction.response.send_message("Gather Data ...")
    IM = imdb.Cinemagoer()
    
    Rmovie = IM.search_movie(movie)
    Film = IM.get_movie(Rmovie[0].movieID)
   
    length = Film.get('runtimes')
    Genre = Film.get('genres')
    Rating = Film.get('rating')
    Name = Film.get('title')
    Cover = Film.get('full-size cover url')
    Desc = Film.get('plot outline')

    embedVar = discord.Embed(title=Name ,color=0x008200)
    if len(Desc) > 256:
        Desc = Desc[:253] + " ..."

    embedVar.description = Desc

    if timestart != None:
        embedVar.add_field(name="We will be streaming at ", value=timestart,inline=False)
    else:
        embedVar.add_field(name="We will be streaming at ", value="Now")

    embedVar.add_field(name="Genre: ", value= ' / '.join(Genre) , inline=False)
    embedVar.add_field(name="Length: ", value=datetime.timedelta(minutes=int(length[0])), inline=True)
    embedVar.add_field(name="IMBD Rating: ", value=Rating, inline=True)
    embedVar.set_image(url=Cover)
    await interaction.edit_original_response(content="<@&834170793000435762>" , embed=embedVar)
    #await interaction.edit_original_response(embed=embedVar)
    
############################################ To add clash of clans tracker #######################################################

############################################ Functions ###########################################################################

async def DownloadSong(Video):
    song_there = os.path.isfile("song"+str(Functionality["NumberTrack"])+".mp3")
    if song_there:
        os.remove("song"+str(Functionality["NumberTrack"])+".mp3")
        print("Removed old song file")

    Functionality["Queue"]["Songs"].append("song"+str(Functionality["NumberTrack"])+".mp3")
   
    Location = "./song"+str(Functionality["NumberTrack"])+".mp3"
    ydl_opts['outtmpl'] = str(Location)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Downloading audio now\n")
        info_dict = ydl.extract_info(Video, download=False)
        await asyncio.get_event_loop().run_in_executor(concurrent.futures.ThreadPoolExecutor(), ydl.download, [Video])
        #ydl.download([Video])

    
    print(Functionality["Queue"]["Songs"])
    Functionality["NumberTrack"] = Functionality["NumberTrack"] + 1
    Functionality["Queue"]["Thumbnail"].append(info_dict.get('thumbnail'))
    Functionality["Queue"]["Name"].append(info_dict.get('title', None))
    Functionality["Queue"]["Duration"].append(info_dict.get('duration'))

def playsong(voice,interaction):
    voice.play(discord.FFmpegPCMAudio(Functionality["Queue"]["Songs"][0]), after=lambda e: NextSong(interaction))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1.0


def NextSong(DisUser):
    if Functionality["PlayingSong"] == False:
        return

    Functionality["PlayingSong"] = False
    
    Functionality["Queue"]["Thumbnail"].pop(0)
    Functionality["Queue"]["Name"].pop(0)
    Functionality["Queue"]["Duration"].pop(0)
    songtoremove = Functionality["Queue"]["Songs"][0]
    Functionality["Queue"]["Songs"].pop(0)

    if len(Functionality["Queue"]["Songs"]) == 0:
        return
    Functionality["PlayingSong"] = True
    voice = get(bot.voice_clients, guild=DisUser.guild)
    playsong(voice,DisUser)

    os.remove(songtoremove)
    #await DisUser.response.send_message(content="Now Playing 🎵"+ Functionality["Queue"]["Name"][0] +"🎵")


def Search_Youtube(search):
    query_string = urllib.parse.urlencode({"search_query" : search})
    html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
    search_results = re.findall(r"watch\?v=(\S{11})", html_content.read().decode())

    end = str("http://www.youtube.com/watch?v=" + search_results[0])
    return end

async def JoinVoiceChannel(DisUser):
    try:
        Channel = DisUser.user.voice.channel
        voice = get(bot.voice_clients, guild=DisUser.guild)
        if voice and voice.is_connected():
            await voice.move_to(Channel)
        else:
            voice = await Channel.connect()
            print(f"The bot has connected to {Channel}\n")
        Functionality["VoiceChannel"] = Channel
        return Channel
    except Exception as err:
        print("not in voice channel ",err)
        return False


bot.run(token)
