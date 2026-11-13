# Answer sheet (template)

**What the CP4 instructions expect this to hold:** the right answers for one test chat, so that results can be scored. For a benchmark, the instructions ask for clear datasets and metrics. For a user study, they ask for the materials.

Used by both tracks. Copy it to a file like `answer_key_01.md`, with the same number as its test chat, and fill in the copy. Line numbers are the ones in the test chat (see [test_chat_TEMPLATE.md](test_chat_TEMPLATE.md)).

- **Chat:** [ the test chat's file name ]
- **Made by:**
- **Checked by:** [ someone who didn't make the chat ]
- **Date checked:**

## Planted mistakes

One row for each mistake hidden in the chat.

| Line | Type | Spec line | Subtle or obvious | Why |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

The Type column uses one of the failure types in `app/prompts/judge.schema.v1.json`, written exactly like this:

- persona drift
- memory loss
- factual contradiction
- knowledge-boundary violation
- style drift
- situational mismatch
- persona exit
- invented claim about the user

The Spec line column holds the ID of the spec line the mistake breaks, like C17.

## Decoys

A decoy is a line that looks like a mistake but is fine. A flag on a decoy counts as a wrong flag.

| Line | What it looks like | Why it is fine |
| --- | --- | --- |
|  |  |  |

## Clean lines

Every other line of the character's. A flag on a clean line counts as a wrong flag.

| Lines | Note |
| --- | --- |
|  |  |
