# How to Run the Cultural Thought-Starter System

A guide for non-technical users. No coding or AI background required.

---

## What this is

A monthly process that turns a curated list of cultural magazines into a short brief of "thought-starters" — sharp, testable cultural reads aimed at a specific brand category (e.g. Nike, performance athletics).

It runs in three layers:
1. **Harvest** — the AI reads ~14 cultural publications and writes a one-paragraph summary of each interesting recent piece.
2. **Tag** — the AI sorts those summaries against five enduring human needs (Connection, Coping, Agency, Vitality, Status), plus an "Unsettled" pool for the strange ones.
3. **Generate** — given a target category and a few brand constraints, the AI proposes ~30 thought-starters drawn from the tagged signals.

You then curate the brief — keep the sharp ones, reject the dull ones, ask for stranger versions where it falls flat.

The whole monthly cycle takes about 2–3 hours of attended work, mostly waiting and reading.

---

## What you need before you start

1. **A Mac or Linux laptop.** (Windows works but isn't covered here.)
2. **Claude Code installed.** This is Anthropic's command-line AI tool. Install via:
   ```
   curl -fsSL claude.ai/install.sh | bash
   ```
   Then run `claude` once and follow the login prompts. You'll need a Claude.ai paid plan (Pro or Max).
3. **The project folder.** It lives at:
   ```
   ~/Desktop/stuff/AI Builds/cultural-thought-starter/
   ```
   If you're picking this up from someone else, copy that folder onto your machine. The whole system is in there.

You don't need an Anthropic API key. The system runs through your Claude.ai subscription.

---

## Two ways to use this system

**Mode A — Monthly cadence.** Harvest broadly across all sources, tag everything, then run any category against that signal pool when one lands. Best when you want a standing capability and don't yet know which categories will come in. Lower urgency per run; richer signal pool.

**Mode B — Ad hoc for a specific brand challenge.** A pitch lands, you have 24–72 hours, you need cultural depth fast. You bias the source list toward what matters for *this* category, harvest tighter, and skip straight to a focused generation. Or, if a recent monthly harvest exists, you skip harvesting entirely and run Phase 2 against the existing pool.

If you're running this regularly, do both — Mode A monthly, then Mode B whenever a brief lands, reusing the most recent monthly harvest as the signal pool. That's the highest-leverage setup.

The Mode A walkthrough is below. The Mode B walkthrough follows it.

---

## Mode A — Monthly cadence

The pattern is: **you tell the AI what to do in plain English, the AI does it, you check the result, you tell it the next thing.** The AI does the reading, the writing, and the file management. You do the judgment.

There are three "stop and check" gates between phases. Don't skip them. The whole thing falls apart if a bad harvest gets tagged and a bad tag gets turned into a brief.

### Step 1 — Open the project in Claude Code

Open the Terminal app (Spotlight → "Terminal").

Type:
```
cd ~/Desktop/stuff/AI\ Builds/cultural-thought-starter/
claude
```

You should now see the Claude Code prompt. The AI has automatically read `CLAUDE.md` (the project's playbook) so it already knows what this project is.

### Step 2 — Phase 0: Harvest

Tell the AI:
> Run the monthly cultural harvest. Use the source list in `sources.yaml`. Output to `signals.json`.

It will work through the source list one by one, using its web-search tool to pull recent articles and write summaries. Expect this to take **30–60 minutes**. It's fine to leave it running and check back.

It may pause and ask whether to drop a source that isn't returning enough. Default answer: **drop it for now, note it in the file, move on.** A source that's dead this month may be live next month.

**What good output looks like**

When it finishes, ask it:
> Show me a summary of what you harvested — counts per source and a few example summaries.

You should see:
- 8–15 items per working source
- Summaries that are *specific* (a name, a place, a claim) — not generic ("an article about contemporary art")
- Recent dates (within the last ~90 days, give or take)

**What bad output looks like**

- A source returned 2 items: the URL is probably wrong. Ask the AI to investigate and fix.
- A source returned 50 items: dedup is broken. Ask the AI to re-run that source.
- Summaries are vague ("a piece about culture"): ask the AI to re-do that source with a higher specificity bar.

**The gate.** Don't move to Step 3 until summaries are specific and counts are reasonable. If they're not, fix and re-run.

### Step 3 — Phase 1: Tag

Tell the AI:
> Run Phase 1. Tag every signal in `signals.json` against the five substrates. Output to `tagged_signals.json`.

This is faster — usually **15–30 minutes**. The AI reads each summary, decides whether it's "forward-looking" enough to keep, and assigns it to one of: Connection, Coping, Agency, Vitality, Status, or Unsettled.

**What good output looks like**

Ask the AI:
> Show me pool counts and 3 example signals from each substrate.

You should see:
- Roughly 10–15% of items dropped (typical)
- Each pool has at least 8–10 items (Status often has more — that's normal)
- The "Unsettled" pool contains the strangest, most cross-cutting signals — these are the most generative for Phase 2
- Tags feel intuitively correct when you read 3–4 examples

**What bad output looks like**

- One source dominates one substrate (e.g. 80% of "Vitality" came from one magazine). Ask the AI to re-tag with awareness of that bias.
- Tags feel arbitrary or flatly wrong on a sample of 5. Ask the AI to walk through its reasoning on those 5, and re-run.

**The gate.** Don't move to Step 4 until you trust the tags on a spot-check.

### Step 4 — Phase 2: Generate the brief

This is where you bring the brand. You need to give the AI:
1. **Category.** "Nike, performance athletics."
2. **Audience.** "Committed amateur athletes — marathon runners, team-sport players."
3. **Conventions to disrupt.** "Tech cues, trail/outdoor metaphors, category fragmentation." (i.e. tropes that are clichéd in the category and the brief should *avoid*.)
4. **What this brief is for.** "A pitch for a repositioning toward pure performance / victory."

Tell the AI:
> Run Phase 2 against this category context: [paste the four items above]. Output to `brief_<category>.md`.

This takes **20–40 minutes**. The output is a markdown document with about 30 thought-starters, organized by substrate.

### Step 5 — Curate the brief

This is the part that takes judgment. Read every thought-starter and decide: **win, loss, or true-but-not-insightful.**

- **Win** — this would change the next brief a strategist wrote. Save it.
- **Loss** — this is wrong, generic, off-strategy, or "gobbly goop" (metaphorical without operational ground). Reject it.
- **True but not insightful** — correct but a strategist could have arrived at it without this whole pipeline. Ask the AI for a stranger re-read.

Tell the AI your verdicts in plain language:
> Numbers 1, 4, 7, 12, 18 are wins. Number 3 is a loss — too metaphorical. Numbers 5, 9, 14 are true but not insightful — give me stranger versions that preserve the strangeness of the source signals.

**What "stranger" means.** When a source signal is weird (kink, suffering, rule-bending, shadow material), a clean translation flattens it. "Stranger" means: keep the uncomfortable register. The insight is in what a strategist *wouldn't* say in a meeting because it would sound weird, not in what they would say because it sounds reasonable.

**Two tests for a winning thought-starter:**
1. Does it name something the audience actually does or is, that current category marketing pretends isn't there? (Example: "Most committed amateur athletes are training broken. Marketing pretends otherwise. The brand that names the brokenness wins.")
2. Does it land on operational ground — something the strategist can act on without a second metaphorical leap? If you have to think "okay, but what does that mean for the brief," it's not there yet.

**Once you've curated**, ask the AI:
> Update the brief: mark rejected items REJECTED with today's date, replace re-reads with the stranger versions, and add a "signals that fed this" block under each accepted thought-starter showing the source articles.

The signal-feed block makes the brief auditable — anyone reading it can see exactly which cultural articles produced each thought-starter.

### Step 6 — Save the result

The final brief is `brief_<category>.md` in the project folder. Copy it wherever it needs to go — Slack, Google Drive, a deck.

Keep `signals.json` and `tagged_signals.json` in the project folder. Next month's run can compare against them to flag what's drifting.

---

## Mode B — Ad hoc for a specific brand challenge

Use this when a brief lands and you need cultural depth fast. The whole cycle compresses to **1–3 hours of attended work** depending on whether you're harvesting fresh or reusing an existing pool.

The big shift from Mode A: **you start with the brand, not the source list.** The brand context shapes which sources to weight, which date range to pull, and which substrates to emphasize.

### Step 1 — Decide: fresh harvest, or reuse?

Open Terminal and check when you last harvested:
```
cd ~/Desktop/stuff/AI\ Builds/cultural-thought-starter/
ls -l signals.json
```

The modification date tells you how old the existing pool is.

- **Less than 45 days old → reuse it.** Skip to Step 4. The signals are still fresh enough; harvesting again would just add hours for marginal lift.
- **45–90 days old → judgment call.** If the brand category is fast-moving (entertainment, internet, fashion) reharvest. If it's slower (architecture, food, design) reuse.
- **More than 90 days old → reharvest.** Signals get stale.

If reusing, you can also do a *targeted top-up* — reharvest only the 4–6 sources most relevant to the category, append to existing `signals.json`, and re-tag. This is faster than a full reharvest.

### Step 2 — Write the brand brief block

Before you open Claude Code, write a short block in plain English. Five things:
1. **Brand and category.** "Aesop, premium personal care."
2. **The challenge.** "Pitch for a campaign repositioning around the rituals of solitude rather than the rituals of indulgence."
3. **Audience.** "Urban professional women 28–45, design-literate, skeptical of wellness language."
4. **Conventions to disrupt.** Three to five tropes the category overuses that the brief should avoid. ("Spa imagery, 'self-care,' minimalist still-lifes of products on stone.")
5. **What sharper would look like.** One sentence: if this brief surprised you, what would it be saying? You don't have to know the answer — naming the question helps the AI aim.

This block is the most important input to the whole run. The AI is downstream of it. Sloppy brand brief, sloppy thought-starters.

### Step 3 — Tune the source list (only if reharvesting)

Open `sources.yaml`. Tell the AI:
> Here's the brand brief: [paste brief block]. Walk through `sources.yaml` and tell me which sources are highest-signal for this category, which are medium, and which are low. Suggest 1–3 sources NOT currently on the list that I should add for this run.

The AI will give you a weighted list. You'll typically harvest:
- 6–10 high-signal sources at full density (8–15 items each)
- 4–6 medium-signal sources at lower density (4–6 items each)
- Skip the low-signal sources for this run

For ad hoc, you don't need 130+ signals. **40–70 well-aimed signals is enough** and produces sharper output than a broad pool.

If the AI suggests adding sources, vet them yourself before accepting — the source list has been carefully curated for editorial register, and a hasty addition can dilute output. Add no more than 2 new sources per ad hoc run.

### Step 4 — Run a focused harvest (skip if reusing)

Tell the AI:
> Run a focused harvest against the brand brief I just gave you. Use the source weighting we agreed on. Date range: last 60 days. Bias toward signals that intersect the category challenge — don't filter to category-specific content, but flag intersections in the summary. Output to `signals.json`.

The "intersect, don't filter" instruction is important. You don't want only-Aesop-relevant signals — you want the full cultural signal pool with intersections noted, so the cross-category strangeness can do its work in Phase 2.

Inspect output the same way as Mode A. Same gate.

### Step 5 — Tag with category awareness

Tell the AI:
> Run Phase 1 tagging. Use the brand brief to inform tagging — when a signal could go in two substrates, lean toward the one that's most generative for this category challenge. Output to `tagged_signals.json`.

For a personal-care/ritual brand: lean Vitality and Coping. For a luxury brand: lean Status with Unsettled cross-cuts. For a community/social product: lean Connection and Agency. For a performance/sport brand (the Nike test case): lean Coping, Agency, Vitality.

The Unsettled pool always matters — it's where the strange cross-cuts live, and ad hoc runs especially benefit from those because the category-aligned thought-starters can otherwise sound predictable.

### Step 6 — Generate with focus

Tell the AI:
> Run Phase 2 against the brand brief. Generate 10–15 thought-starters (not 30) — sharper, fewer, deeper. Bias selection toward the [Vitality / Coping / Unsettled] pool. Apply the strangeness-preserved register: name what the audience actually does or is that current category marketing pretends isn't there. Output to `brief_<brand>.md`.

The smaller count is deliberate. In ad hoc mode, you don't have time to curate 30. You want 10–15 candidates, with 6–8 surviving curation as wins.

If the AI surfaces too many "true but not insightful" thought-starters, push back:
> These are too clean. Re-do with the source signals' strangeness preserved — particularly anything from the Unsettled pool that includes shadow material (suffering, rule-bending, kink, refusal).

### Step 7 — Curate fast

Same trichotomy as Mode A — win, loss, true-but-not-insightful — but tighter. In ad hoc you're aiming for 4–6 wins to take into a pitch, not a comprehensive cultural map.

Two extra ad hoc questions to ask while curating:
1. **Does this give the strategist a new line they can write today?** If yes, it's a win regardless of whether it'd survive a monthly run.
2. **Does this risk being misread by the client as off-strategy?** Note the risk in the brief alongside the thought-starter — pitch teams need to know which moves are "definitely safe" vs "sharper but defendable."

Once curated, ask:
> Update the brief: rejected items marked REJECTED, signal-feed traceability under each accepted thought-starter, and a one-line "pitch posture" note on each (safe / defendable / sharp).

### Step 8 — Hand off

The brief is `brief_<brand>.md`. Copy into the pitch deck working doc, share with the strategist or creative lead, run a 20-minute live read-through with them so they can flag anything that doesn't translate to their line of attack.

Save the file with a date suffix (`brief_aesop_2026_05_03.md`) — ad hoc briefs are point-in-time documents tied to a specific pitch, not living docs.

### When to combine modes

If a Mode A monthly harvest is fresh (under 45 days), Mode B collapses to Steps 2 + 6 + 7 + 8. You skip harvesting and tagging entirely — the signal pool already exists, you just generate against it with new brand context. This is the **fastest, highest-leverage path** and the main argument for keeping the monthly cadence going even when no specific pitch is on the calendar.

A typical year might look like: monthly harvest standing, 8–12 ad hoc generations off it. Each ad hoc generation takes 30–60 minutes once the harvest is current.

---

## Editing the source list

`sources.yaml` is the editorial filter. It's the most important file in the system. Don't change it casually, but do edit when:

- A source dies. Mark it `fetchable: false` with a note.
- A source's URL changes. Update the `base_url`.
- You want to add a publication. Add an entry following the format of others. Tell the AI:
  > I added a new source to `sources.yaml`. Run a small-batch test on just that source and report what you find before adding it to the regular monthly run.

The list is curated for *editorial register*, not coverage. The bias is toward independent voices, design-school output, and unusual cultural critics — not trade press or product reviews.

---

## Common problems and what to do

**"The AI ran out of context / lost track of what it was doing."**
Tell it:
> Read `CLAUDE.md` and the relevant output file (`signals.json` or `tagged_signals.json`) and pick up where you left off.

The project files are designed to be the source of truth. Anything the AI did is on disk.

**"The AI is asking me too many questions."**
Tell it:
> Use auto mode for the rest of this phase. Use your judgment on routine decisions. Only stop and ask if something is genuinely ambiguous.

**"The thought-starters all sound the same / sound like a generic strategy deck."**
This usually means Phase 1 over-tagged everything into Status (the "branding for status" default). Re-run Phase 2 with a specific instruction:
> Bias toward signals from the Unsettled pool and from Coping. Avoid Status-substrate signals unless they specifically subvert a status convention.

**"A source is hard-blocked / returns nothing."**
Some publishers (Pitchfork, Thingtesting, anything Instagram) block automated readers. Mark them `fetchable: false` and move on. Don't waste time trying to crack them — the editorial diversity in the rest of the list is enough.

**"I don't know if the AI is doing it right."**
Ask:
> Show me your work. Walk me through the last three decisions you made and why.

The AI will write out its reasoning. If it sounds shallow or off, push back.

---

## What "good" looks like — example

A win from the Nike run:

> **The broken-athlete line.** Most committed amateurs are training broken — managing some pain, some old injury, some compromise their coach doesn't fully know about. Current performance marketing pretends this isn't happening; the brand that names brokenness as the *condition*, not the failure, wins the room.

Why this is a win:
- Names something the audience actually does/is (training broken)
- Inverts a marketing pretense (that committed athletes are uninjured)
- Lands on operational ground (you can write the brief from this directly)
- Source-traced (came from specific cultural signals about welfare, suffering-as-condition, the etymology essays on infohazards)

A loss from the Nike run:

> **Air, not place.** Drawing from Maya Man's piece on the internet-as-air, what if Nike repositioned around an idea of athletic effort as atmospheric — not located on a trail or a court but everywhere the athlete moves?

Why this is a loss:
- Requires a metaphorical leap (internet → air → athletic atmosphere) before the operational implication lands
- "Gobbly goop" — sounds smart, doesn't change what the strategist writes tomorrow

---

## A short glossary

- **Substrate** — one of the five enduring human needs the system tags against. Connection (belonging), Coping (managing felt weight), Agency (doing things with intention), Vitality (aliveness, embodiment), Status (where you stand).
- **Unsettled pool** — the bucket for signals that don't fit cleanly into one substrate. Often the most generative for thought-starter generation because they cut across categories.
- **Forward-looking** — a signal flagged as pointing at something *changing* in the culture, not just describing the present. The Phase 1 tag drops items that aren't forward-looking.
- **Thought-starter** — a sharp, testable cultural read aimed at a target brand category. Not a tagline, not a campaign idea — a *frame* the strategist can build on.
- **Strangeness-preserved translation** — a translation that keeps the uncomfortable register of the source signal instead of filing it down to operational tidy. The high-yield translation register for this system.
- **Phase gate** — a "stop and check" moment between phases. The system fails if you skip them; bad harvest → bad tag → bad brief, and you won't catch it.

---

## When in doubt, ask the AI

This is the most important rule. The AI in the loop knows the project (it auto-loads `CLAUDE.md` every session), knows the previous decisions, and can explain what it's doing. If anything is unclear, ask it in plain English. You don't need to know the technical machinery — you need to know what *good output looks like* and how to push back when it doesn't.
