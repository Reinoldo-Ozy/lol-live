#!/usr/bin/env python3
import asyncio
import io
import json
import logging
import os
import time
from collections import deque
from pathlib import Path

import datetime

import discord
import requests

import render
import styles
from discord import app_commands
from discord.ext import tasks

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REGISTRY = DATA / "registry.json"
KEYFILE = Path.home() / ".config" / "lol-live" / "key"
RIOT_KEYFILE = Path.home() / ".config" / "lol-analise" / "key"

PLATFORMS = {
    "br1": "americas", "na1": "americas", "la1": "americas", "la2": "americas",
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
    "kr": "asia", "jp1": "asia", "oc1": "sea", "ph2": "sea", "sg2": "sea",
}
QUEUES = {420: "Solo/Duo", 440: "Flex", 400: "Normal Draft", 430: "Normal Blind",
          450: "ARAM", 490: "Quickplay", 700: "Clash", 1700: "Arena"}
ROLES = {"TOP": "topo", "JUNGLE": "jungla", "MIDDLE": "meio",
         "BOTTOM": "atirador", "UTILITY": "suporte"}
ACCENT = 0xD8F24A
CHANNEL_NAME = "partidas"
STICKY_DELAY = 6
STICKY_MIN_INTERVAL = 20


def env(name, fallback_file=None):
    v = os.environ.get(name, "").strip()
    if v:
        return v
    if fallback_file and Path(fallback_file).exists():
        return Path(fallback_file).read_text().strip()
    return ""


RIOT_KEY = env("RIOT_API_KEY", RIOT_KEYFILE)
TOKEN = env("DISCORD_TOKEN", KEYFILE)


def load():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def save(reg):
    DATA.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False))


_champs = {}


def champion_name(cid):
    global _champs
    if not _champs:
        try:
            ver = requests.get("https://ddragon.leagueoflegends.com/api/versions.json",
                               timeout=15).json()[0]
            data = requests.get(
                f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/pt_BR/champion.json",
                timeout=25).json()["data"]
            _champs = {int(v["key"]): v["name"] for v in data.values()}
        except Exception:
            _champs = {}
    return _champs.get(cid, f"campeão {cid}")


_hits = deque()


def throttle():
    while True:
        now = time.monotonic()
        while _hits and now - _hits[0] > 120:
            _hits.popleft()
        if len(_hits) < 95:
            _hits.append(now)
            return
        time.sleep(max(0.2, 120 - (now - _hits[0]) + 0.2))


def riot_get(url):
    throttle()
    for attempt in range(3):
        r = requests.get(url, headers={"X-Riot-Token": RIOT_KEY}, timeout=15)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 3)) + 1)
            continue
        if r.status_code in (401, 403):
            raise RuntimeError("chave da Riot inválida ou expirada")
        time.sleep(1 + attempt)
    return None


def account_name(puuid, platform="br1"):
    regional = PLATFORMS.get(platform, "americas")
    acc = riot_get(f"https://{regional}.api.riotgames.com/riot/account/v1/"
                   f"accounts/by-puuid/{puuid}")
    return f"{acc['gameName']}#{acc['tagLine']}" if acc else "?"


def account_by_id(name, tag, platform="br1"):
    regional = PLATFORMS.get(platform, "americas")
    return riot_get(f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/"
                    f"by-riot-id/{requests.utils.quote(name, safe='')}/"
                    f"{requests.utils.quote(tag, safe='')}")


def live_game(puuid, platform="br1"):
    return riot_get(f"https://{platform}.api.riotgames.com/lol/spectator/v5/"
                    f"active-games/by-summoner/{puuid}")


def spectate_link(game, platform):
    key = (game.get("observers") or {}).get("encryptionKey")
    if not key:
        return None
    return f"lolspectator://spectator/{platform.upper()}/{game['gameId']}/{key}"


class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.reg = load()
        self.games = {}
        self.names = {}
        self.ranks = {}
        self.panels = {}
        self.notices = {}
        self.teams = {}
        self.images = {}
        self.sticky_tasks = {}
        self.last_repost = {}

    async def setup_hook(self):
        self.poll.start()
        await self.tree.sync()

    async def on_guild_join(self, guild):
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        except Exception as e:
            print("erro no sync:", e)
        channel = await self.ensure_channel(guild)
        if channel:
            await self.update_panel(guild.id, force=True)
        print(f"entrou em {guild.name} · canal {channel}")

    async def refresh_players(self):
        mudou = False
        for gid, cfg in self.reg.items():
            players = cfg.get("players", {})
            for pu, p in list(players.items()):
                try:
                    name, tag = p["riot"].rsplit("#", 1)
                    acc = await asyncio.to_thread(account_by_id, name, tag,
                                                  p.get("platform", "br1"))
                except Exception as e:
                    print("refresh:", e)
                    continue
                if not acc or acc["puuid"] == pu:
                    continue
                novo = acc["puuid"]
                players.pop(pu, None)
                p = dict(p)
                p["puuid"] = novo
                players[novo] = p
                self.ranks.pop(pu, None)
                self.games.pop(pu, None)
                mudou = True
                print(f"puuid atualizado: {p['riot']}")
        if mudou:
            save(self.reg)

    async def on_ready(self):
        await self.refresh_players()
        for guild in self.guilds:
            ch = self.get_channel(self.reg.get(str(guild.id), {}).get("channel") or 0)
            if ch:
                await self.recover_panel(str(guild.id), ch)
                await self.update_panel(str(guild.id), force=True)
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            except Exception as e:
                print("sync guild:", e)
        for guild in self.guilds:
            if not self.reg.get(str(guild.id), {}).get("channel"):
                ch = await self.ensure_channel(guild)
                if ch:
                    await self.update_panel(guild.id, force=True)
        n = sum(len(c.get("players", {})) for c in self.reg.values())
        await self.set_presence()
        print(f"logado como {self.user} · {len(self.guilds)} servidor(es) · {n} jogadores")

    async def ensure_channel(self, guild):
        gid = str(guild.id)
        cfg = self.reg.setdefault(gid, {"channel": 0, "players": {}})
        ch = guild.get_channel(cfg.get("channel") or 0)
        if ch:
            return ch
        ch = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
        if not ch:
            cat = discord.utils.find(
                lambda c: "league" in c.name.lower() or "lol" in c.name.lower(),
                guild.categories)
            try:
                ch = await guild.create_text_channel(
                    CHANNEL_NAME, category=cat,
                    topic="Avisos de partida · /registrar Nick#TAG",
                    reason="canal de avisos do lol-live")
            except discord.Forbidden:
                print(f"sem permissao para criar canal em {guild.name}")
                return None
            except discord.HTTPException as e:
                print("erro ao criar canal:", e)
                return None
        cfg["channel"] = ch.id
        save(self.reg)
        if ch.category is None:
            cat = discord.utils.find(
                lambda c: "league" in c.name.lower() or "lol" in c.name.lower(),
                guild.categories)
            if cat:
                try:
                    await ch.edit(category=cat)
                except discord.HTTPException:
                    pass
        return ch

    TIER_ORDER = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
                  "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]

    def rank_score(self, entry):
        if not entry:
            return -1
        t = entry.get("tier", "").upper()
        tier = self.TIER_ORDER.index(t) if t in self.TIER_ORDER else 0
        div = {"IV": 1, "III": 2, "II": 3, "I": 4}.get(entry.get("rank", ""), 0)
        return tier * 10000 + div * 1000 + int(entry.get("leaguePoints", 0))

    async def panel_embed(self, gid):
        cfg = self.reg.get(gid, {})
        players = list(cfg.get("players", {}).values())
        rows = []
        for p in players:
            entry = await asyncio.to_thread(self.rank_of, p["puuid"],
                                            p.get("platform", "br1"))
            rows.append((self.rank_score(entry), p, entry))
        rows.sort(key=lambda r: -r[0])
        linhas = []
        for i, (score, p, entry) in enumerate(rows, 1):
            g = self.games.get(p["puuid"])
            extra = ""
            if g:
                me = next((x for x in g["participants"]
                           if x.get("puuid") == p["puuid"]), None)
                extra = f" 🔴 {champion_name(me['championId']) if me else 'em partida'}"
            linhas.append(f"`{i:02d}` **{p['riot']}** · {render.rank_text(entry)}{extra}")
        emb = discord.Embed(
            timestamp=discord.utils.utcnow(),
            title="Jogadores vigiados",
            description="\n".join(linhas) or "Ninguém cadastrado.\nUse `/registrar Nick#TAG`.",
            color=ACCENT)
        emb.set_footer(text=f"{len(players)} jogador(es) · rankeado por elo de solo queue"
                            f" · /registrar · /remover")
        return emb

    async def update_panel(self, gid, force=False):
        gid = str(gid)
        cfg = self.reg.get(gid)
        if not cfg:
            return
        ch = self.get_channel(cfg.get("channel") or 0)
        if not ch:
            return
        msg = self.panels.get(gid)
        now = time.monotonic()
        if not force and msg and now - self.last_repost.get(gid, 0) < STICKY_MIN_INTERVAL:
            return
        emb = await self.panel_embed(gid)
        if msg:
            try:
                await msg.edit(embed=emb, attachments=[])
                self.last_repost[gid] = now
                return
            except discord.HTTPException as e:
                print("erro ao editar painel:", e)
        new = await ch.send(embed=emb)
        self.panels[gid] = new
        self.last_repost[gid] = now
        if msg:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass

    async def send_notice(self, gid, p, game):
        gid = str(gid)
        cfg = self.reg.get(gid)
        ch = self.get_channel(cfg.get("channel") or 0) if cfg else None
        if not ch:
            return
        gkey = game["gameId"]
        team = await self.enrich(game, p.get("platform", "br1"), p["puuid"])
        buf = await asyncio.to_thread(styles.build_6, team)
        link = spectate_link(game, p.get("platform", "br1"))
        me = next((x for x in game["participants"] if x.get("puuid") == p["puuid"]), None)
        champ = champion_name(me["championId"]) if me else "?"
        role = ROLES.get((me or {}).get("teamPosition", ""), "")
        emb = discord.Embed(
            timestamp=discord.utils.utcnow(),
            title=f"{p['riot']} entrou em partida",
            description=(f"**{champ}**" + (f" · {role}" if role else "")
                         + f" · {QUEUES.get(game.get('gameQueueConfigId'), game.get('gameMode'))}"
                         + f" · {game.get('gameLength', 0) // 60} min")
                        + (f"\n`{link}`" if link else ""),
            color=ACCENT)
        emb.set_image(url="attachment://partida.png")
        try:
            msg = await ch.send(embed=emb, file=discord.File(buf, "partida.png"))
            self.notices.setdefault(gid, {})[gkey] = msg.id
        except discord.HTTPException as e:
            print("erro ao enviar aviso:", e)

    async def drop_notice(self, gid, game_id):
        gid = str(gid)
        cfg = self.reg.get(gid)
        ch = self.get_channel(cfg.get("channel") or 0) if cfg else None
        mid = self.notices.get(gid, {}).pop(game_id, None)
        if ch and mid:
            try:
                await ch.get_partial_message(mid).delete()
            except discord.HTTPException:
                pass

    async def move_panel(self, gid):
        gid = str(gid)
        cfg = self.reg.get(gid)
        if not cfg:
            return
        ch = self.get_channel(cfg.get("channel") or 0)
        if not ch:
            return
        old = self.panels.get(gid)
        emb = await self.panel_embed(gid)
        new = await ch.send(embed=emb)
        self.panels[gid] = new
        self.last_repost[gid] = time.monotonic()
        if old:
            try:
                await old.delete()
            except discord.HTTPException:
                pass

    async def recover_panel(self, gid, ch):
        try:
            async for m in ch.history(limit=50):
                if m.author.id != self.user.id or not m.embeds:
                    continue
                e = m.embeds[0]
                if (e.title or "") in ("Jogadores vigiados", "Partidas ao vivo"):
                    if not self.panels.get(str(gid)):
                        self.panels[str(gid)] = m
                elif e.image:
                    try:
                        await m.delete()
                    except discord.HTTPException:
                        pass
        except discord.HTTPException:
            pass

    def schedule_sticky(self, gid):
        gid = str(gid)
        task = self.sticky_tasks.get(gid)
        if task and not task.done():
            return

        async def run():
            try:
                await asyncio.sleep(STICKY_DELAY)
                await self.move_panel(gid)
            except Exception as e:
                print("sticky:", e)
            finally:
                self.sticky_tasks.pop(gid, None)

        self.sticky_tasks[gid] = asyncio.create_task(run())

    async def on_message(self, msg):
        if msg.author.bot or not msg.guild:
            return
        cfg = self.reg.get(str(msg.guild.id))
        if cfg and cfg.get("channel") == msg.channel.id:
            self.schedule_sticky(msg.guild.id)

    async def set_presence(self):
        total = sum(len(c.get("players", {})) for c in self.reg.values())
        vivos = sum(1 for g in self.games.values() if g)
        nome = (f"{vivos} em partida" if vivos else f"{total} jogador(es)")[:128]
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=nome))

    def rank_of(self, puuid, platform):
        hit = self.ranks.get(puuid)
        if hit and time.monotonic() - hit[1] < 1800:
            return hit[0]
        try:
            data = riot_get(f"https://{platform}.api.riotgames.com/lol/league/v4/"
                            f"entries/by-puuid/{puuid}") or []
        except Exception:
            data = []
        solo = next((e for e in data if e.get("queueType") == "RANKED_SOLO_5x5"), None)
        self.ranks[puuid] = (solo, time.monotonic())
        return solo

    async def enrich(self, game, platform, focus=None):
        out = []
        for p in game["participants"]:
            pu = p["puuid"]
            riot = p.get("riotId") or self.names.get(pu)
            if not riot:
                riot = await asyncio.to_thread(account_name, pu, platform)
                self.names[pu] = riot
            entry = await asyncio.to_thread(self.rank_of, pu, platform)
            out.append({"teamId": p["teamId"], "championId": p["championId"],
                        "player": riot, "champ": champion_name(p["championId"]),
                        "role": p.get("teamPosition") or "",
                        "watched": pu == focus,
                        "elo": render.rank_text(entry)})
        return out

    async def check_all(self):
        if not self.reg:
            return
        mudou = False
        tocados = set()
        for gid, cfg in list(self.reg.items()):
            if not self.get_channel(cfg.get("channel") or 0):
                continue
            for puuid, p in list(cfg.get("players", {}).items()):
                try:
                    game = await asyncio.to_thread(live_game, puuid,
                                                   p.get("platform", "br1"))
                except Exception as e:
                    print("erro spectator:", e)
                    continue
                antes = self.games.get(puuid)
                novo = game["gameId"] if game else None
                antigo = antes["gameId"] if antes else None
                if novo == antigo:
                    continue
                self.games[puuid] = game
                if novo:
                    await self.send_notice(gid, p, game)
                elif antigo:
                    await self.drop_notice(gid, antigo)
                for old in [k for k in self.images if k == antigo]:
                    self.images.pop(old, None)
                    self.teams.pop(old, None)
                mudou = True
                tocados.add(gid)
                await asyncio.sleep(1)
        if mudou:
            await self.set_presence()
            for gid in tocados:
                await self.update_panel(gid, force=True)

    @tasks.loop(seconds=45)
    async def poll(self):
        await self.check_all()

    def build_embed(self, player, game):
        platform = player.get("platform", "br1")
        me = next((x for x in game["participants"]
                   if x.get("puuid") == player["puuid"]), None)
        champ = champion_name(me["championId"]) if me else "?"
        role = ROLES.get((me or {}).get("teamPosition", ""), "")
        mins = game.get("gameLength", 0) // 60
        embed = discord.Embed(
            timestamp=discord.utils.utcnow(),
            title=f"{player['riot']} entrou em partida",
            description=f"**{champ}**" + (f" · {role}" if role else "") +
                        f"\n{QUEUES.get(game.get('gameQueueConfigId'), game.get('gameMode'))}"
                        f" · {mins} min de jogo",
            color=ACCENT)
        link = spectate_link(game, platform)
        if link:
            embed.add_field(name="Assistir", value=f"```{link}```", inline=False)
            embed.set_footer(text="abre o cliente do LoL · precisa de espectador habilitado")
        else:
            embed.set_footer(text="sem encryptionKey nesta partida")
        return embed


bot = Client()


@bot.tree.error
async def on_app_command_error(inter: discord.Interaction, error):
    print(f"ERRO no comando {inter.command.name if inter.command else '?'}: {error!r}")
    msg = f"erro: {error}"
    try:
        if inter.response.is_done():
            await inter.followup.send(msg, ephemeral=True)
        else:
            await inter.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


@bot.tree.command(name="canal", description="Cria ou define o canal dos avisos")
@app_commands.describe(canal="Canal de texto (vazio = cria #partidas)")
@app_commands.checks.has_permissions(manage_guild=True)
async def canal(inter: discord.Interaction, canal: discord.TextChannel = None):
    print(f"comando /canal de {inter.user} em {inter.guild}")
    gid = str(inter.guild_id)
    cfg = bot.reg.setdefault(gid, {"channel": 0, "players": {}})
    if canal is None:
        canal = await bot.ensure_channel(inter.guild)
        if not canal:
            await inter.response.send_message(
                "não tenho permissão de **Gerenciar Canais** para criar #partidas.\n"
                "Reautorize com o link de convite novo ou use `/canal #algum-canal`.",
                ephemeral=True)
            return
    cfg["channel"] = canal.id
    save(bot.reg)
    await bot.update_panel(gid, force=True)
    await inter.response.send_message(f"avisos vão para {canal.mention}", ephemeral=True)


@bot.tree.command(name="registrar", description="Adiciona um jogador para vigiar")
@app_commands.describe(riot_id="Nick#TAG", plataforma="br1, na1, euw1...")
async def registrar(inter: discord.Interaction, riot_id: str, plataforma: str = "br1"):
    print(f"comando /registrar de {inter.user}: {riot_id} ({plataforma})")
    if "#" not in riot_id:
        await inter.response.send_message("use o formato Nick#TAG", ephemeral=True)
        return
    await inter.response.defer(ephemeral=True)
    name, tag = riot_id.rsplit("#", 1)
    try:
        acc = await asyncio.to_thread(account_by_id, name.strip(), tag.strip(),
                                      plataforma.lower())
    except Exception as e:
        await inter.followup.send(f"erro: {e}", ephemeral=True)
        return
    if not acc:
        await inter.followup.send("conta não encontrada nessa plataforma", ephemeral=True)
        return
    gid = str(inter.guild_id)
    cfg = bot.reg.setdefault(gid, {"channel": 0, "players": {}})
    cfg["players"][acc["puuid"]] = {
        "riot": f"{acc['gameName']}#{acc['tagLine']}",
        "puuid": acc["puuid"], "platform": plataforma.lower(),
    }
    save(bot.reg)
    if not cfg.get("channel"):
        await bot.ensure_channel(inter.guild)
    await bot.update_panel(gid, force=True)
    await bot.set_presence()
    game = await asyncio.to_thread(live_game, acc["puuid"], plataforma.lower())
    estado = "em partida agora" if game else "fora de partida"
    await inter.followup.send(
        f"vigiando **{acc['gameName']}#{acc['tagLine']}** ({plataforma.upper()}) · {estado}",
        ephemeral=True)


@bot.tree.command(name="remover", description="Para de vigiar um jogador")
async def remover(inter: discord.Interaction, riot_id: str):
    gid = str(inter.guild_id)
    cfg = bot.reg.get(gid, {"players": {}})
    alvo = riot_id.lower()
    for pu, p in list(cfg.get("players", {}).items()):
        if p["riot"].lower() == alvo:
            del cfg["players"][pu]
            bot.games.pop(pu, None)
            save(bot.reg)
            await bot.update_panel(gid, force=True)
            await bot.set_presence()
            await inter.response.send_message(f"removido: {p['riot']}", ephemeral=True)
            return
    await inter.response.send_message("não achei esse nick na lista", ephemeral=True)


@bot.tree.command(name="lista", description="Mostra os jogadores vigiados")
async def lista(inter: discord.Interaction):
    cfg = bot.reg.get(str(inter.guild_id), {"players": {}})
    pl = cfg.get("players", {})
    if not pl:
        await inter.response.send_message("ninguém cadastrado ainda", ephemeral=True)
        return
    linhas = []
    for p in pl.values():
        estado = "🔴 em partida" if bot.games.get(p["puuid"]) else "⚪ fora"
        linhas.append(f"{estado} · {p['riot']} ({p['platform'].upper()})")
    await inter.response.send_message("\n".join(linhas), ephemeral=True)


@bot.tree.command(name="painel", description="Reposta o painel no fim do canal")
async def painel(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    await bot.update_panel(str(inter.guild_id), force=True)
    await inter.followup.send("painel atualizado", ephemeral=True)


@bot.tree.command(name="verificar", description="Força uma checagem agora")
async def verificar(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    await bot.check_all()
    await inter.followup.send("checagem feita", ephemeral=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s] [%(levelname)-7s] %(name)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    if not TOKEN:
        raise SystemExit("defina DISCORD_TOKEN ou escreva em ~/.config/lol-live/key")
    if not RIOT_KEY:
        raise SystemExit("defina RIOT_API_KEY ou escreva em ~/.config/lol-analise/key")
    bot.run(TOKEN)
