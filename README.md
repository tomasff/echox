# Echox

Echox is a (hacked together) small utility to backup lectures from Echo360.
It creates an over-engineered index locally using SQLite to keep track of
which lectures have been backed-up.

Run it with
```bash
# (Recommended) with pipx
pipx install git+ssh://git@github.com/tomasff/echox.git

# With pip
pip install --user git+ssh://git@github.com/tomasff/echox.git

echox --config config.toml
```

The TOML configuration file requires,
```toml
# You probably want your browser's user agent here...
user_agent = "User agent"

# Loads at most `chunk_size` bytes while retrieving a media file.
chunk_size = 20480 

# Sections which we want to backup and download media from.
sections = [
    "uuid-v4-1",
    "uuid-v4-2",
]

# Directory where the media and index is created.
media_path = "."
```

In addition, credentials are loaded from the following environment variables,
```bash
ECHO360_EMAIL=...
ECHO360_PASSWORD=...
ECHO360_APP_ID=...
```

Note that `ECHO360_PASSWORD` corresponds to your Echo360 password, but some
institutions rely on their own authentication to access Echo360 instead.
In those cases, you can create an Echo360 password in the Echo360 account
settings.