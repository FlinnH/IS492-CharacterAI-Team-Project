# Prototype

<!-- cp2-templates-v2 -->

The CP2 proof of concept (Step 9). It covers the critical journeys in DESIGN_SPEC.md, enough to demo the decision rights, interrogation moments, and trust cues we claim. CP3's working code goes in /app/, so this folder stays a prototype.

**Format:** HTML, CSS, and JavaScript clickthrough, vibe-coded with Claude Code.

**Link:** [ Vercel link ]

**Owner:** Flynn

## How to open or run it

Double-click `prototype/index.html` to open it in your browser, or use the link above. There is nothing to install or build.

- You need to be online for the Roboto font and the icons. Offline, it still works with the system font and no icons.
- Each screen has its own address, so you can jump straight to one: `index.html#define`, `#run`, `#diagnose`, or `#compare`.
- Reset demo in the top bar puts the demo data back. Reloading the page does the same.

## Demo coverage

> The guide asks the prototype to show the collaboration mechanics from DESIGN_SPEC.md section 7. One row per screen.

| Screen | Journey step (DESIGN_SPEC.md section 2) | Mechanic it shows (7.1, 7.2, or 7.3) | Done? |
| --- | --- | --- | --- |
| Spec editor (`#define`) | Define | 7.1 Decision rights: only the creator can change the spec, and runs stay pinned to v1. Each line ID chip lists the flags that cite that line. | Yes |
| Run a conversation (`#run`) | Stress-test | 7.3 Trust cues: the receipt ID and spec version above the chat, the turn count while it plays, and the number of possible breaks at the end. | Yes |
| Flag review (`#diagnose`) | Diagnose | 7.1 Agree or Override on every flag. 7.2 Agree unlocks only after "Show in context," and an override needs a reason of at least 3 words. 7.3 Confidence chips, evidence quotes, and the "Not checked by the AI" card. | Yes |
| Compare runs (`#compare`) | Repair | 7.1 Only flags the creator didn't override count as breaks, and the "Next step" card leads back to the spec line that broke in both runs. | Yes |

## Slide 6 demo path (60 to 90 seconds)

1. **Run (about 20 seconds).** On Run a conversation, keep Run 1 and press Start run. Let a few turns play, then press Skip to end and Review flags.
2. **Agree with turn 4 (about 20 seconds).** On the turn 4 card, press Show in context. Point out Alex's line, the marked evidence, and the K2 text, then press Agree.
3. **Override turn 3 (about 20 seconds).** On the turn 3 card, press Override, type a reason such as "The reply matches C5," and press Save. This flag is planted: the reply really does match C5. The summary's first break moves from turn 3 to turn 4.
4. **Compare (about 20 seconds).** Open Compare runs. Run 1's first break is now turn 4, K2 broke in both runs, and "Open K2 in the spec" closes the loop back to Define.

## What it does not do yet

> Being explicit here prevents over-promising ahead of CP3.

- No real AI calls. The runs and flags are scripted.
- Nothing is saved. Decisions and reasons live in memory until you reload or press Reset demo, and "Create v2 (demo)" does not make a new spec version.
- The data is made up for the prototype. Only the spec text is real, copied from validation/fixtures/CHARACTER_SPEC.md.
- Only scenario F2 has data. T1, T2, E1, E2, and F1 say "no demo data," and the tool you pick doesn't change the run.
