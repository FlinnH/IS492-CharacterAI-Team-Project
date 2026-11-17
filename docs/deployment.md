# Deploying the public demo

How the workbench gets its public link for CP4, written for someone who has never deployed anything. It covers what the service is, every environment variable, the clicks on Render, how to check the link, and the keep-warm switch.

The link is a demo, not a product. It runs on free plans, and it exists so a grader can open the workbench without installing it.

## What the public link is

Render is a company that runs web apps on its own computers. One free Render "web service" runs the same app that `app/run.sh` runs on a laptop, with one setting changed: `WORKBENCH_MODE=demo`. The file `render.yaml` at the repo root tells Render how to build and start it. Render calls that file a Blueprint.

In demo mode:

- **Each visitor gets a private copy.** The first time a browser opens the link, the server gives it a cookie and its own copy of the starting data: spec v1 and the two sample chats, Claude (CLA-F2) and ChatGPT (GPT-F2), with their saved checks. Nothing one visitor does shows for another.
- **No code is needed to look around.** A visitor can open every screen, read the spec, open the samples, see their flags, press Show in context, Agree, and Undo, and compare the two samples. None of that calls a model.
- **Live AI needs the demo code.** Starting a test case, Free Chat, a typed message, Check this chat, a re-check, an Override, and Import all ask for it. Without it, the button opens a card that says where the code is and links to the README's quick start.
- **Some things are off.** Settings, saving a new spec version, the seeded transcript, and Run All Test Cases.
- **There are limits.** One visitor may start 2 live chats, run 4 AI checks, and run 4 re-checks. All visitors together share 200 model calls a day. A copy that sits idle for 2 hours is deleted.

What the free plan means, from Render's docs (read Nov 16, 2026):

- The service goes to sleep after 15 minutes with no requests. The next visitor waits about one minute while it wakes.
- Every restart, redeploy, or sleep wipes the service's files. Visitors' copies and the day's call count start over. The sample chats come back, because they are built at startup.
- A workspace gets 750 free instance hours a month, which is enough for one service that never sleeps.
- Render's free-plan page does not say a payment card is needed. If Render asks for one, stop and decide before going on.

[architecture.md](architecture.md) says how demo mode is built, and [safety_privacy.md](safety_privacy.md) says what it protects.

## What you need before you start

1. **The GitHub account that owns the repo.** Render deploys from `main`, so it needs access to the repository.
2. **A Render account.** Sign up at render.com. Signing up with GitHub is the shortest way.
3. **A Gemini key for the demo.** Make a new key in Google AI Studio (aistudio.google.com), in a project with no billing set up. With no billing, Google's free quota is the hard stop, so the demo can never cost money. Don't reuse the key from your own `app/.env`.
4. **A demo code.** Any text of 12 characters or more. To make a random one, run this and copy what it prints:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(12))"
   ```

   The code goes in two places only: Render, and the Canvas submission. Never put it in the repo, an issue, a pull request, or a chat.
5. **The tests on `main`.** `.github/workflows/tests.yml` already runs them on every push. Render deploys a commit only after they pass.

## Every environment variable

Environment variables are named values the server reads when it starts. On Render they take the place of `app/.env`, and the demo starts with no `app/.env` file at all.

| Name | Value | Where it comes from |
| --- | --- | --- |
| `GEMINI_API_KEY` | Secret | You type it on Render when you create the Blueprint. It is the demo's own key from Google AI Studio. |
| `WORKBENCH_DEMO_CODE` | Secret | You type it on Render when you create the Blueprint. It is the code you made in the step above. |
| `WORKBENCH_MODE` | `demo` | `render.yaml` |
| `WORKBENCH_HOST` | `0.0.0.0` | `render.yaml`. It lets Render reach the server. |
| `PYTHON_VERSION` | `3.12.10` | `render.yaml`. Render's own setting. Its default Python is newer than the one the tests run on. |
| `WORKBENCH_DAILY_CALL_CAP` | `200` | `render.yaml`. Model calls a day, for all visitors together. |
| `WORKBENCH_DEMO_RUN_LIMIT` | `2` | `render.yaml`. Live chats one visitor may start. Test cases and free chats count together. |
| `WORKBENCH_DEMO_CHECK_LIMIT` | `4` | `render.yaml`. AI checks one visitor may run. |
| `WORKBENCH_DEMO_RECHECK_LIMIT` | `4` | `render.yaml`. Re-checks one visitor may run. |
| `WORKBENCH_DEMO_MAX_VISITORS` | `30` | `render.yaml`. Visitors' copies kept at once. The next new visitor sees "The demo is busy. Try again in a few minutes." |
| `WORKBENCH_DEMO_IDLE_MINUTES` | `120` | `render.yaml`. Idle minutes before a copy is deleted. |
| `PORT` | `10000` | Render sets it by itself. The server listens on it. Never set it by hand. |

Every other setting keeps its default from `app/.env.example`: the Gemini provider, 15 calls a minute, and the models in `app/prompts/models.v5.toml`.

The two secrets are marked `sync: false` in `render.yaml`, which means the file names them and holds no value. Render asks for them once.

## Deploy it: the clicks on Render

Do this once. It takes about 10 minutes.

1. Open dashboard.render.com and sign in.
2. Click **New**, then **Blueprint**.
3. If Render has not been connected to GitHub yet, it asks you to connect. Follow its steps, and give it access to this repository only.
4. In the list of repositories, find `IS492-CharacterAI-Team-Project` and click **Connect**.
5. Give the Blueprint a name, like `workbench-demo`. Set the branch to `main`. Leave **Blueprint Path** as it is, since `render.yaml` sits at the repo root.
6. Render reads `render.yaml` and lists what it will make: one web service on the free plan. It shows a box for each secret:
   - `GEMINI_API_KEY`: paste the demo's Gemini key.
   - `WORKBENCH_DEMO_CODE`: paste the demo code.
7. Check that the plan says **Free**. Then click **Deploy Blueprint**.
8. Open the new service. Its **Events** or **Logs** page shows the build. The first build takes a few minutes while Render installs `app/requirements.txt`. It is done when the log says the service is live.
9. The service's page shows its address, like `https://character-consistency-workbench.onrender.com`. If that name was taken, Render adds a few letters to it. This address is the public link.

If no deploy starts, the newest commit on `main` may have no finished test run yet. Render skips a commit that has no checks, or a failed one. Wait for the Tests workflow to go green on GitHub (the Actions tab). Then, on the service's **Deploys** page, open **Manual Deploy** and click **Deploy latest commit**.

## Check the link

First, from the repo root, run the checker with the link's address. It asks what a browser would ask, with no demo code and no model call:

```bash
app/.venv/bin/python app/scripts/check_link.py https://character-consistency-workbench.onrender.com
```

Every line should start with `ok`. A line that starts with `FAIL` names what is wrong.

Then check by hand in a private window, so you see what a brand-new visitor sees. In Chrome that is File, New Incognito Window.

1. **The page and the banner.** Open the link. A band at the top says "Public demo. Don't type anything personal". The top bar has **Demo code** where Settings would be. On **Run Test Cases**, the Chat menu lists Claude (CLA-F2) and ChatGPT (GPT-F2).
2. **The samples work with no code.** Open **Flag review**. Press **Show in context** on a flag, then **Agree**, then **Undo**. Each one works, and nothing asks for a code.
3. **Live AI asks for the code.** On **Run Test Cases**, press **Start Test**. A card opens: "Live AI needs a demo code", with a link to the README. There is no Settings button and no Run All Test Cases button.
4. **The code unlocks it.** Type the demo code and press **Unlock**. The run starts, and Harry's replies arrive a few words at a time. When it ends, press **Check this chat** and wait for the flags.
5. **Visitors are apart.** Open the link in a normal window too. Its Chat menu shows only the two samples, not the run you just made, and it asks for the code again.
6. **The limits hold.** Back in the private window, start a second chat, then press **Start Test** a third time. A card says you've used this demo's live chats. On **Spec editor**, **Edit spec** opens a card that says it is off in the public demo.

Three things to watch on the first deploy, because Render's docs don't say:

- **Streaming.** In check 4, replies should grow a few words at a time. If each reply appears all at once, the host is holding the stream back. The demo still works, only less lively.
- **A long check.** Check this chat can take up to a minute. If it fails at about 30 seconds every time, tell the team.
- **Time zones.** The daily count follows Pacific time. If the build log shows an error that names `ZoneInfo` or `tzdata`, add `tzdata` to the end of `buildCommand` in `render.yaml`.

## The keep-warm switch

A sleeping demo makes its first visitor wait about a minute. `.github/workflows/keep-warm.yml` can ask the demo's health address every 10 minutes, so it stays awake. It is off until you turn it on.

To turn it on:

1. On GitHub, open the repository's **Settings**, then **Secrets and variables**, then **Actions**.
2. Open the **Variables** tab and click **New repository variable**.
3. Name it `DEMO_HEALTH_URL`. For the value, type the link with `/api/health` on the end, like `https://character-consistency-workbench.onrender.com/api/health`.
4. Click **Add variable**.

To turn it off, delete the variable. To try it once by hand, open the **Actions** tab, pick **Keep the demo warm**, and click **Run workflow**.

What to know:

- It always finishes green, even when the demo is asleep or down. Render deploys only when every check on `main` passes, so a red run here would block a deploy.
- GitHub runs scheduled jobs late when it is busy, so the demo can still sleep now and then.
- Kept awake all month, one service uses about 744 of the 750 free hours. Turn keep-warm on for the weeks that matter, like the grading window, and off afterward.
- After turning it on, look at the service's **Deploys** page an hour later. It should show no new deploys. If it shows one every 10 minutes, delete the variable.

## Change something later

- **A limit.** Edit its value in `render.yaml` and merge the change to `main`. Render reads the file again and restarts the service. A value changed in Render's dashboard can be put back by the file the next time Render reads it, so the file is the place to change it.
- **The Gemini key or the demo code.** On the service's page, click **Environment** in the left pane, change the value, and save with **Save and deploy**. Change the code in the Canvas submission too.
- **The app itself.** Merge to `main`. When the tests pass, Render deploys the new commit by itself. A failed test means no deploy, and the old version keeps running.
- **Take the link down.** Delete the service on Render, from its **Settings** page. Delete the `DEMO_HEALTH_URL` variable on GitHub as well.

## When something goes wrong

| What you see | What to do |
| --- | --- |
| The page takes a minute to open | The service was asleep. It is awake now. Turn on keep-warm if this matters. |
| "The demo is busy. Try again in a few minutes." | Every copy is in use. Copies free up after 2 idle hours. To allow more, raise `WORKBENCH_DEMO_MAX_VISITORS` in `render.yaml`. |
| A card says today's AI calls are used up | The daily cap was reached. The count starts over at midnight Pacific time. The samples still work. |
| "There's no Gemini key yet" on Start Test | `GEMINI_API_KEY` is empty on Render. Set it under **Environment**. |
| The service won't start, and the log says `WORKBENCH_DEMO_CODE` | The code is missing or shorter than 12 characters. Set it under **Environment**. |
| A reply fails with "its free limit was reached" | Google's free quota for the minute or the day is used. Wait, or lower `WORKBENCH_DAILY_CALL_CAP`. |
| A push to `main` didn't change the link | The tests failed or haven't finished. Look at the Actions tab on GitHub. |
| Agree or Unlock says the demo takes changes only from its own page | The browser sent the request from another address. Open the link itself, not a copy of the page. |
| The link is down during the presentation | Run the workbench on a laptop with `app/run.sh`, as the README says, and show that. |

Only the person whose Render account holds the service can change its secrets or delete it. Everyone else can still change the app and the limits through pull requests to `main`.

## Try demo mode on your laptop

To see demo mode without Render, start the app with the mode set, on its own port and its own database folder:

```bash
WORKBENCH_MODE=demo WORKBENCH_DEMO_CODE=any-code-you-like WORKBENCH_PORT=8493 WORKBENCH_DB_PATH=data/demo-check/workbench.db app/run.sh
```

It opens http://127.0.0.1:8493. Use Chrome or Firefox for this: the visitor cookie is marked Secure, and Safari keeps a Secure cookie only on an https address. A normal window and a private window count as two visitors. Live AI uses the key in your `app/.env`, and only after you type the code. Stop it with Ctrl+C, and delete `app/data/demo-check/` when you are done.
