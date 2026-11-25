# Putting GemXpert online at gemxpert.4axismedia.com

The site lives in `Web/` (Vite + React + TypeScript + three.js). Vercel builds it and hosts it for you; your domain then points
at Vercel. Nothing here needs a server of your own. Plan on about 30 minutes, most of it waiting for DNS.

You'll need:

* a **GitHub** account (free) - github.com
* a **Vercel** account - vercel.com → *Sign Up* → *Continue with GitHub*. The free *Hobby* plan is for personal,
  non-commercial projects; a site used commercially by 4axismedia needs the *Pro* plan (check vercel.com/pricing).
* access to the place where **4axismedia.com** is registered (GoDaddy, Namecheap, Cloudflare, ...), to add one DNS record.

## 1. Put the code on GitHub

1. github.com → **New repository** → name it `gemxpert`, choose *Private*, **don't** add a README → *Create repository*.
2. GitHub shows the repository address, e.g. `https://github.com/YOUR-NAME/gemxpert.git`. In a terminal in the `GemXpert` folder:

```powershell
git remote rename origin upstream
```

```powershell
git remote add origin https://github.com/YOUR-NAME/gemxpert.git
```

```powershell
git push -u origin main
```

(The first command keeps the original repository reachable as `upstream`. Git asks you to sign in to GitHub the first time.)

## 2. Create the Vercel project

1. vercel.com → **Add New… → Project** → find `gemxpert` → **Import**.
2. **Root Directory → Edit → choose `Web`**. This matters: the repository also holds the Unity project and Blender files.
3. Framework Preset shows **Vite**; leave the build settings as they are (`vercel.json` sets them).
4. *Optional* - **Environment Variables**: add `ANTHROPIC_API_KEY` with a key from console.anthropic.com if you want
   "Design from a photo" to work. Everything else works without it. Every analysed photo costs API credit on that key, and the
   site is public, so set a monthly spend limit in the Anthropic Console.
5. **Deploy**. After a minute you get an address like `gemxpert-xyz.vercel.app`. Open it and check the ring, the hand and
   *Wearable Device → Connect wearable*.

## 3. Connect gemxpert.4axismedia.com

1. In the Vercel project: **Settings → Domains → Add** → type `gemxpert.4axismedia.com` → *Add*.
2. Vercel shows a DNS record to create, normally:

   | Type | Name | Value |
   |---|---|---|
   | CNAME | `gemxpert` | `cname.vercel-dns.com` (copy the exact value Vercel shows; it may be a project-specific one) |

3. At your domain registrar, open **DNS settings for 4axismedia.com**, add that CNAME record, save.
   Only add this one record; don't change the existing records for `4axismedia.com` or `www`.
4. Back in Vercel the domain turns from *Invalid Configuration* to *Valid* - usually within minutes, at most a few hours.
   Vercel issues the HTTPS certificate on its own.

Done: **https://gemxpert.4axismedia.com**. HTTPS is also what lets Chrome use Bluetooth for the wearable.

## 4. Updating the site later

Change the code, commit, then:

```powershell
git push
```

Vercel rebuilds and publishes in about a minute. Every pull request also gets its own preview address.

## Running it on your PC

```powershell
cd Web
```

```powershell
npm install
```

```powershell
npm run dev
```

Open http://localhost:5173. For photo analysis locally, copy `Web/.env.example` to `Web/.env.local` and put your key in it.
