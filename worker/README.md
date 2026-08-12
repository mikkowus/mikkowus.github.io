# Setting up the paddlespots Worker (one-time)

This sets up the little server (a "Cloudflare Worker") and database that
`add-location.html`, `review.html`, and `import-takeout.html` talk to. You
only need to do this once. It's free on Cloudflare's free plan for this
amount of traffic.

## What you need first

- [Node.js](https://nodejs.org) installed on your computer (any recent
  version).
- A free [Cloudflare account](https://dash.cloudflare.com/sign-up) — just an
  email + password, no credit card needed for this.
- A terminal, with this repo checked out, `cd`'d into the `worker` folder:
  ```
  cd worker
  ```

Run every command below from inside that `worker` folder.

## 1. Install the tools

```
npm install
```

## 2. Log in to Cloudflare

```
npx wrangler login
```

This opens a browser tab — click "Allow" to connect your Cloudflare account.
You can close the tab once it says you're logged in.

## 3. Create the database

```
npx wrangler d1 create paddlespots-db
```

This prints something like:

```
[[d1_databases]]
binding = "DB"
database_name = "paddlespots-db"
database_id = "1234abcd-....."
```

Copy that `database_id` value. Open `wrangler.jsonc` in this folder, find the
line that says:

```
"database_id": "REPLACE_WITH_DATABASE_ID_FROM_WRANGLER_D1_CREATE",
```

and paste your id in there instead, so it looks like:

```
"database_id": "1234abcd-.....",
```

Save the file.

## 4. Set up the database's tables

```
npx wrangler d1 migrations apply paddlespots-db --remote
```

Type `y` if it asks to confirm. This creates the (empty) tables the Worker
needs.

## 5. Add yourself as the owner

Pick a name and a private access code (just something only you know — this
isn't a real password system, it's meant for a small trusted group). Then
run:

```
node scripts/hash-code.js "YourName" "your-access-code" owner
```

This prints out a command that looks like:

```
npx wrangler d1 execute paddlespots-db --remote --command="INSERT INTO contributors ..."
```

Copy that whole printed line and run it (paste it into the terminal and
press enter). That adds you to the database as the **owner** — the only role
that can review/approve submissions.

To add other trusted people later, repeat this step for each person, but
use `contributor` instead of `owner` at the end — contributors can submit
new locations but can't review/approve.

## 6. Deploy the Worker

```
npx wrangler deploy
```

This prints a URL at the end, something like:

```
https://paddlespots-api.your-account.workers.dev
```

Copy that URL — you'll need it in the next step.

## 7. Point the site at your Worker

Open these three files in the main repo folder (not the `worker` folder):

- `add-location.html`
- `review.html`
- `import-takeout.html`

In each one, find this line near the top of the `<script>` section:

```js
const API_BASE = location.hostname === 'localhost' || location.hostname === '127.0.0.1'
  ? 'http://localhost:8787'
  : 'https://paddlespots-api.YOUR-SUBDOMAIN.workers.dev';
```

Replace `https://paddlespots-api.YOUR-SUBDOMAIN.workers.dev` with the URL
you copied in step 6. Save all three files, commit, and push (or edit them
directly on GitHub) so the live site picks up the change.

## 8. Try it out

Visit `add-location.html` on the live site, log in with the name and code
from step 5, and submit a test location. Then visit `review.html`, log in
with the same name/code, and you should see it waiting for review.

## Adding more trusted people later

Just repeat step 5 with their name and a code you give them (role
`contributor`, not `owner`). No redeploy needed — it's just a database row.

## Already deployed before? Pick up new migrations

If you already ran steps 1–6 once (like for the initial `add-location.html`
setup) and this repo has since added a new `migrations/*.sql` file, re-run
step 4 to apply it to your existing database — migrations that already ran
are skipped automatically, only new ones apply:

```
npx wrangler d1 migrations apply paddlespots-db --remote
```

## Optional: the bulk Takeout import tool (`import-takeout.html`)

`add-location.html`/`review.html` work without this. This is only needed if
you want to use `import-takeout.html` to bulk-import a whole Google Takeout
Maps list at once (it geocodes named places via the Google Places API).

1. Get a Google Maps Platform API key with the **Places API** enabled
   (console.cloud.google.com → APIs & Services → Credentials) — if you've
   already used the separate Takeout-extraction tool
   (`~/projects/2026_google_saved_data_extraction`), you already have one in
   its `.env` file and can reuse it.
2. Store it as a Worker secret (never put it in `wrangler.jsonc` — secrets
   there would be committed to git in plaintext):
   ```
   npx wrangler secret put GOOGLE_MAPS_API_KEY
   ```
   Paste the key when prompted, then re-run `npx wrangler deploy` so the
   Worker picks it up.
3. That's it — `import-takeout.html` (owner-only, same login as `review.html`)
   will now be able to geocode named places. Google's Places "Find Place from
   Text" endpoint has a small per-request cost, so a big Takeout list (dozens
   to hundreds of named places) isn't free, but it's the same cost you'd pay
   running the Python extraction tool for the same data.

## If something doesn't work

- **"no such table" error**: step 4 didn't run, or ran against the wrong
  database — re-run `npx wrangler d1 migrations apply paddlespots-db --remote`.
- **Login says "Invalid name or code"**: double check the name matches
  exactly (case-sensitive) what you used in step 5, and re-run
  `node scripts/hash-code.js` if you're unsure of the code you picked.
- **The page can't reach the Worker at all**: make sure step 7 was saved on
  the *live* site (not just locally) and that the URL doesn't have a typo.
- Cloudflare's dashboard (dash.cloudflare.com → Workers & Pages → your
  worker) shows live logs if you want to see what a failing request looked
  like.
