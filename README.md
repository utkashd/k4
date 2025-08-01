# K4

A ChatGPT-style interface built for server-side extensibility.

## setup

Haven't yet tested setup on a fresh machine. But this probably works.

### requirements

- [docker desktop](https://docs.docker.com/desktop/) (or anything that gives you
  the docker compose CLI)
- An LLM API key

Gemini has a [free tier](https://ai.google.dev/gemini-api/docs/pricing), though
I don't recommend it for anything beyond quick testing.

### steps

#### clone the repo

```zsh
git clone git@github.com:utkashd/k4.git
cd k4
```

#### run K4

<details>

<summary>use `smake` (recommended)</summary>

```zsh
./smake dev
```

This is just running `docker compose up` along with some extra conveniences
(ensures docker desktop is running, removes any old dangling images, prints some
useful messages). **You are encouraged to read exactly what this does before
running it: <https://github.com/utkashd/k4/blob/main/smake>**

Now you can navigate to <http://localhost:5173>. The server will be
<http://localhost:8000>, and if you care, the API docs are at
<http://localhost:8000/docs>. Setup is now done.

When you are done, you can stop K4 with

```zsh
./smake stop
```

which is basically just running `docker compose stop`.

</details>

<details>

<summary> OR use `docker compose up`</summary>

```zsh
K4_ENVIRONMENT=development docker compose up --build -d
```

and stop K4 with

```zsh
docker compose down
```

</details>
