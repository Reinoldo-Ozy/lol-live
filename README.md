# lol-live

Bot de Discord que vigia jogadores e avisa quando eles entram em partida,
com o link de espectador do cliente do LoL.

## Como funciona

- `/registrar SeuNick#TAG` guarda o `puuid` do jogador no servidor.
- A cada 45 s o bot consulta `spectator-v5` para cada jogador cadastrado.
- Quando a partida começa, posta um embed no canal configurado com campeão,
  posição, fila, tempo de jogo, o time e o link `lolspectator://`.
- O estado é por `gameId`: o aviso sai uma vez por partida.

## 1. Criar o bot

1. <https://discord.com/developers/applications> → **New Application**.
2. Aba **Bot** → **Reset Token** → copie o token.
3. Aba **OAuth2 → URL Generator**: escopos `bot` + `applications.commands`;
   permissões `Send Messages` e `Embed Links`. Use a URL gerada para convidar.
4. Guarde o token:

```bash
mkdir -p ~/.config/lol-live && chmod 700 ~/.config/lol-live
printf '%s' 'SEU_TOKEN' > ~/.config/lol-live/key
chmod 600 ~/.config/lol-live/key
```

A chave da Riot é lida de `~/.config/lol-analise/key` (a mesma do dashboard),
ou de `RIOT_API_KEY`.

## 2. Rodar

```bash
cd ~/Projects/lol-live
.venv/bin/python bot.py
```

Comandos no Discord:

| comando | o que faz |
|---|---|
| `/canal #avisos` | define o canal (precisa de Gerenciar Servidor) |
| `/registrar Nick#TAG [plataforma]` | adiciona jogador (padrão `br1`) |
| `/remover Nick#TAG` | remove |
| `/lista` | mostra quem está vigiado e quem está em partida |
| `/verificar` | força uma checagem agora |

## 3. Deixar rodando

```bash
systemctl --user edit --force --full lol-live.service
```

```ini
[Unit]
Description=LoL live tracker
After=network-online.target

[Service]
WorkingDirectory=/home/reinoldo/Projects/lol-live
ExecStart=/home/reinoldo/Projects/lol-live/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now lol-live
journalctl --user -u lol-live -f
```

## Limitações

- O link `lolspectator://spectator/{PLATAFORMA}/{gameId}/{encryptionKey}` abre o
  **cliente** do LoL; no Linux (sem cliente) ele não tem para onde ir. Teste o
  formato no seu cliente — se o seu não abrir, me avise que ajusto.
- O jogador precisa ter **espectador habilitado** (padrão em ranqueada).
- Partida custom/treino e alguns modos não aparecem no spectator.
- O estado fica em memória: reiniciar o bot no meio de uma partida gera um
  aviso repetido.
- A chave da Riot de desenvolvimento expira em 24 h; troque o arquivo quando
  o bot começar a logar `chave da Riot inválida ou expirada`.
- `spectator-v5` custa 1 request por jogador a cada 45 s. Com 20 jogadores são
  ~27 req/min, dentro do limite de 100/2min.
