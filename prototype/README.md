# Prototype

<!-- cp2-templates-v2 -->

The CP2 proof of concept (Step 9). It covers the critical journeys in DESIGN_SPEC.md, enough to demo the decision rights, interrogation moments, and trust cues we claim. CP3's working code goes in /app/, so this folder stays a prototype.

**Format:** HTML, CSS, and JavaScript clickthrough, vibe-coded with Claude Code.

**Link:** [is492-characterai-team-project-prot.vercel.app](https://is492-characterai-team-project-prot.vercel.app)

**Owner:** Flynn

## What it is, in one minute

The Character Consistency Workbench helps people who write AI characters find out where and why a character breaks. Our test character is Harry Potter after book 4. You move through four screens, one per step of our journey:

1. **Define** (Spec editor): read the character's rules, each with a line ID like K2.
2. **Stress-test** (Run a conversation): play a real chat between a tester, Alex, and Harry.
3. **Diagnose** (Flag review): the AI proposes possible breaks, called flags, and you make the call on each one.
4. **Repair** (Compare runs): see where each tool's chat broke, and which spec line to fix next.

The idea we test is human-in-the-loop review. The AI checks every turn, but you decide what counts as a break. So the screens show the evidence behind every flag, make you open it before you agree, ask for a reason when you override, and keep the open calls in view until you finish.

## How to open or run it

Double-click `prototype/index.html` to open it in your browser, or use the link above. There is nothing to install or build.

- You need to be online for the Roboto font and the icons. Offline, it still works with the system font and no icons.
- Each screen has its own address, so you can jump straight to one: `index.html#define`, `#run`, `#diagnose`, or `#compare`.
- Reset demo in the top bar puts the starting data back. Reloading the page does the same.
- The Light and Dark buttons in the top bar switch the theme. It starts from your system setting.
- To serve it locally instead, for example in the Claude desktop app's browser panel, run this from the repo folder and open `http://localhost:8000`:

```bash
python3 -m http.server 8000 --directory prototype
```

## Reading the codes

The "What do the codes mean?" button in the top bar explains these too, and every spec line chip has a tooltip.

| Code | Meaning | Example |
| --- | --- | --- |
| T, E, F | Scenarios: a typical case, an edge case, and a failure case. T1 is a normal chat, T2 reviewing a transcript, E1 a long chat, E2 an emotional chat, F1 "you're an AI," and F2 things Harry can't know yet. | F2 |
| C, R, K, B | Spec lines: a canon fact, a relationship, a knowledge limit, and a behavior rule | K2 is knowledge-limit line 2 |
| CLA, GPT, GEM | Chats: the tool code, then the scenario. CLA is Claude, GPT is ChatGPT, and GEM is Gemini. | CLA-F2 is Claude running F2 |

## Demo coverage

> The guide asks the prototype to show the collaboration mechanics from DESIGN_SPEC.md section 7. One row per screen.

| Screen | Journey step (DESIGN_SPEC.md section 2) | Mechanic it shows (7.1, 7.2, or 7.3) | Done? |
| --- | --- | --- | --- |
| Spec editor (`#define`) | Define | 7.1 Decision rights: only the creator can change the spec, and runs stay pinned to v1. Each line ID chip lists the flags that cite that line. | Yes |
| Run a conversation (`#run`) | Stress-test | 7.3 Trust cues: the Tool dropdown picks a real chat, and its receipt ID, spec version, and where it came from sit above the chat. The turn count shows while it plays, and the number of possible breaks at the end. | Yes |
| Flag review (`#diagnose`) | Diagnose | 7.1 Agree or Override on every flag, and every open flag says "Needs your call," counted by a badge on the tab. 7.2 Agree unlocks only after "Show in context," and an override needs a reason of at least 3 words. 7.3 Confidence chips, evidence quotes, and the "Not checked by the AI" card. The chat switcher moves between tools and shows the calls left in each. | Yes |
| Compare runs (`#compare`) | Repair | 7.1 Only flags the creator didn't override count as breaks, a notice warns while flags are still open, and the "Next step" cards lead back to the spec lines that broke in every chat. | Yes |

## Slide 6 demo path (60 to 90 seconds)

1. **Run (about 20 seconds).** On Run a conversation, keep Claude in the Tool dropdown and press Start run. Let a few turns of CLA-F2 play, then press Skip to end and Review flags. Point out the badge on the Flag review tab: 6 flags across both chats need your call.
2. **Agree with turn 4 (about 20 seconds).** On the turn 4 card, press Show in context. Point out Alex's line, Harry's guess "Is she from the Ministry or something?", and the K2 text, then press Agree.
3. **Override turn 3 (about 20 seconds).** On the turn 3 card, press Override, type a reason such as "Harry says Ireland won," and press Save. This flag is planted: we scored the turn Pass, because the reply matches C17. The summary now reads 1 agreed, 1 overridden, and the badge is down to 4.
4. **Compare (about 20 seconds).** Open Compare runs. The notice says 4 flags still need your call and count as breaks until you decide. Claude's turn 3 square is now dashed, both chats first broke at turn 2 (too long), and K2 and B4 broke in both chats. "Open K2 in the spec" closes the loop back to Define.

## Where the data comes from

- **The spec** is copied word for word from validation/fixtures/CHARACTER_SPEC.md.
- **The two chats** are real: CLA-F2 and GPT-F2, copied word for word from the full conversation logs in validation/transcripts/claude_outputs.md and chatgpt_outputs.md.
- **The flags** are written by hand from our scores in those files. Each probe we scored Fail or Partial gets a flag citing the line from the F2 probe key in validation/PROMPTING_PROTOCOL.md, plus one flag for the first quick check that broke. Claude's turn 3 flag is planted and wrong on purpose, so the demo can show an override. The interface never marks it as wrong.

## How the code is organized

| File | What it holds |
| --- | --- |
| `index.html` | The page shell: top bar, tabs, the four screens, and the dialogs |
| `styles.css` | Material 3 tokens (light and dark), components, and each screen's layout |
| `data.js` | All the data, in one object: the spec, the F2 script, and the chats with their flags |
| `app.js` | The behavior: one render function per screen, the router, dialogs, and tooltips |

Everything you change lives in memory, and `data.js` is never edited by the page. To add another tool's chat, for example GEM-F2 in CP4, add one more entry to `runs` in `data.js` with its tool, receipt, replies, and flags. The Tool dropdown, the chat switcher, the badge, and Compare runs pick it up with no other changes. A tool other than ChatGPT, Claude, or Gemini also needs adding to `TOOLS` in `app.js`.

## What it does not do yet

> Being explicit here prevents over-promising ahead of CP3.

- No live AI calls. The two chats, CLA-F2 and GPT-F2, are real chats played back word for word from their logs.
- The flags are written by hand from our scores, not by an AI reviewer. One of them, Claude's turn 3 flag, is planted and wrong on purpose, so the demo can show an override.
- Nothing is saved. Decisions and reasons live in memory until you reload or press Reset demo, and "Create v2 (demo)" does not make a new spec version.
- Only scenario F2 is loaded, with one chat each from Claude and ChatGPT. Gemini shows "no chat yet," and the other scenarios show "not in this prototype." Loading more than one scenario needs a change to `data.js`, which holds a single script today.
