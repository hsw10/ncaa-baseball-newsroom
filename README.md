# Division I NCAA Baseball Newsroom

A public, static Division I college-baseball news dashboard with **NCAA Baseball News** plus conference groupings for the **SEC**, **ACC**, **Big Ten**, **Big 12**, and **Mid-Major** coverage (AAC, Sun Belt, C-USA, WCC, and more).

Each section displays five current, topical stories from a conference-specific Google News search and links directly to the originating publisher. Select a conference name or its **View all** link to open a conference-specific page with up to 15 stories.

## Refreshes

- GitHub Actions refreshes `data.json` daily at 13:00 UTC: 8:00 AM EST (9:00 AM EDT).
- The page itself is hosted through GitHub Pages.

## Local preview

```bash
python3 refresh.py
python3 server.py
# open http://127.0.0.1:8787/
```

The hosted GitHub Pages site is read-only; its data is refreshed by the workflow. The local preview's update control runs `refresh.py` through `server.py`.

## Sources

Article cards are sourced from conference-specific Google News searches and link directly to their original publishers. Conference logos and article imagery remain property of their respective owners.