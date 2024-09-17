Authentication

-   [ ] Switch to refresh token + short-lived access token
-   [ ] hash user passwords

-   [ ] documentation
    -   [ ] setup guide (improve names of entities)
-   [ ] improve hass tool store:
    -   [x] summary
    -   [ ] test vacuum, climate, media controls. find other stuff worth testing
-   [x] tear out factoid stuff for now
-   display chat history
-   [ ] deployment
    -   [ ] single docker container
    -   [ ] docker compose
-   [x] display system messages

-   address all code TODOs
-   improve css/styling
-   remove the websocket proxy
-   improve tool store: include summary of tools available
-   auth for users? (use something more secure and out-of-the-box, like google?)
-   fix websocket bugs
-   avoid race conditions with file io stuff
-   option to keep gpt home running (uses more memory, less compute)
-   better device/entity descriptions (it keeps thinking that smart plugs are light
    switches)
-   make easily extensible. marketplace for additional features
-   avoid assertions in python backend
-   first-time flow for setting system message (pronouns, "act as X character" nonsense)

# GptHome

An opinionated, ChatGPT-style interface for Home Assistant.
