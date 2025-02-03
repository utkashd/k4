# Creating a new package

<!-- To quick-preview in VSCode: Cmd+K, V -->

```zsh
cd <repo root>/backend/packages
uv init --package <new package name>
cd src/<new package name>
touch py.typed
```

Don't forget to add your new package as a dependency where it's needed, e.g.:

```zsh
cd <repo root>/backend
uv add <new package name>
```

You may need to restart VSCode for the IDE to stop complaining about imports.

And now you can start coding in the directory that was created

## Add a dependency

```zsh
cd <repo root>/backend/packages/<new package name>
uv add <dependency name>
```
