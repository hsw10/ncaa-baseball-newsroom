# Division I NCAA Baseball Newsroom

A public, static Division I college-baseball news dashboard with **NCAA Baseball News** plus conference groupings for the **SEC**, **ACC**, **Big Ten**, **Big 12**, and **Mid-Major** coverage (AAC, Sun Belt, C-USA, WCC, and more).

Each section displays five current, topical stories from a conference-specific Google News search and links directly to the originating publisher. Select a conference name or its **View all** link to open a conference-specific page with up to 15 stories.

## Refreshes

- Automatic refreshes are disabled. Use **Scan & update** on the dashboard, sign in to GitHub, and select **Run workflow** to scan and publish the latest stories.
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

### SEC coverage sources

The SEC section combines league-wide reporting from SEC Sports, D1Baseball, Baseball America, WholeHogSports, and The Advocate with official baseball coverage from all 16 member programs: Alabama, Arkansas, Auburn, Florida, Georgia, Kentucky, LSU, Ole Miss, Mississippi State, Missouri, Oklahoma, South Carolina, Tennessee, Texas, Texas A&M, and Vanderbilt.

### ACC coverage sources

The ACC section combines ACC Sports, D1Baseball, Baseball America, ESPN, and established team-beat coverage with official baseball coverage from all 16 current ACC baseball programs: Boston College, California, Clemson, Duke, Florida State, Georgia Tech, Louisville, Miami, North Carolina, NC State, Notre Dame, Pittsburgh, Stanford, Virginia, Virginia Tech, and Wake Forest. (SMU and Syracuse are ACC members but do not sponsor varsity baseball.)