# Why a company should like this

- data privacy: deploy your own LLM (full privacy) or trust an API provider
- customizable and extensible for company-specific use-cases
- not subject to many complex regulations that ruin the experience or add costs
- deployed in and only accessible through your private cloud
- no contract renewal pains, no switching costs from me

Authentication

- [x] hash user passwords
- [ ] Switch to sessions instead of JWT. Use keydb to cache sessions

- [ ] documentation
  - [ ] setup guide (improve names of entities)
- [ ] deployment
  - [ ] docker compose
- [x] display system messages

- address all code TODOs
- improve css/styling
- remove the websocket proxy
- improve tool store: include summary of tools available
- auth for users? (use something more secure and out-of-the-box, like google?)
- fix websocket bugs
- avoid race conditions with file io stuff
- option to keep cyris running (uses more memory, less compute)
- better device/entity descriptions (it keeps thinking that smart plugs are light
    switches)
- make easily extensible. marketplace for additional features
- avoid assertions in python backend
- first-time flow for setting system message (pronouns, "act as X character" nonsense)

Things I've learned

- docker: more comfortable with command line, better understanding of containers,
    images, etc. more comfortable with writing dockerfiles
- SQL: prepared statements, connection pools
- FastAPI + Uvicorn, async-await w python
- Basic React webapp
- python package management (with uv)
- basics of auth, jwts vs sessions, how to implement at scale

## Cyris

An opinionated, ChatGPT-style interface for Home Assistant.
