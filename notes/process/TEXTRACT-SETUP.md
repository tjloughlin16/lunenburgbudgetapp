# Amazon Textract: setting it up, on this machine or another

Textract reads scanned pages into TABLES -- cells with a row and a column already assigned --
which is the part of reading the annual reports that took weeks by hand (CLAUDE.md 13b).
It is billed in DOLLARS on an AWS account, not against the Claude plan, so it has its own
spend meter and its own cut-off. First set up 27 October 2026.

## What exists, and where

| piece | where | what it is for |
|---|---|---|
| `scripts/textract_pages.py` | repo | reads pages through the meter; caches every response |
| `scripts/textract_spend.py` | repo | the meter: ledger, caps, the latch, AWS's own figure |
| `scripts/aws/setup_textract.sh` | repo, run in CloudShell | creates everything in AWS below. Safe to re-run |
| `scripts/aws/copy_setup.sh` | repo | puts the setup on the clipboard, wrapped for pasting |
| IAM user `lunenburg-textract` | AWS | the ONLY credential on a laptop. Textract + read its own budget. Nothing else -- S3 and IAM are denied (checked) |
| policy `LunenburgTextractDeny` | AWS | denies all Textract. Attached by the budget, never by hand |
| role `LunenburgTextractBudgetAction` | AWS | lets AWS Budgets attach that one policy to that one user |
| budget `lunenburg-textract` | AWS | $60/month of Textract; emails at 50% / 80% / forecast 100%; at 100% actual it attaches the deny policy automatically |
| `~/.aws/credentials`, profile `lunenburg-textract` | each machine | the key. Never in git, never pasted into a Claude session |
| `build/textract/` | each machine, gitignored | `ledger.csv` (every paid page), `cache/` (every paid response), `out/` (the TSVs) |
| `build/STOP-TEXTRACT` | each machine | the latch. While it exists nothing is sent |

**The limits, in the order they trip:** the run ceiling (twice the run's estimate) → our
monthly cap, `MONTHLY_CAP_USD = 50` in `textract_spend.py` (raising it is a commit) → the
latch, which then stays on until a person deletes it → AWS's budget action at $60, which
works even if none of our code is running.

## A new machine, when the AWS side already exists

1. Python libraries: `python3 -m pip install boto3 awscli`
   (Homebrew's `awscli` failed on the Intel Mac under macOS 26 -- it wanted to build from
   source with Command Line Tools too old for that. The pip package has the same `aws configure`.)
2. A key for this machine. In AWS CloudShell, signed in as the owner:

       aws iam create-access-key --user-name lunenburg-textract

   A user may hold two keys. If it already has two, delete the one from the machine you
   retired first: `aws iam list-access-keys --user-name lunenburg-textract`, then
   `aws iam delete-access-key --user-name lunenburg-textract --access-key-id AKIA...`.
3. In your OWN terminal (not through Claude -- the secret would land in the transcript):

       aws configure --profile lunenburg-textract      # key, secret, us-east-1, json

4. Check it:

       aws sts get-caller-identity --profile lunenburg-textract   # ends in user/lunenburg-textract
       python3 scripts/textract_spend.py --status                 # "AWS budget $..." not "not readable"

**The ledger is per machine.** A second machine starts at $0 and does not see the first
one's spend, so our monthly cap is per machine while AWS's $60 budget covers the account.
Run Textract from ONE machine at a time. Moving for good: copy `build/textract/` across
(the cache is paid for -- re-reading it is free, re-fetching it is not).

## From nothing: a new AWS account, or the setup was deleted

1. Sign in to https://console.aws.amazon.com as the account owner; region **US East (N. Virginia)**.
2. On the laptop: `bash scripts/aws/copy_setup.sh` -- the script is now on the clipboard,
   wrapped as `cat > setup_textract.sh <<'LUNENBURG_EOF' ...`. **Never paste the bare script:**
   `set -e` and `exit` in a pasted line close the CloudShell session.
3. Open CloudShell (the `>_` icon in the top bar), paste, press Enter. Check the paste arrived whole:

       wc -l setup_textract.sh && tail -1 setup_textract.sh     # 111 lines, ending in `fi`

   A `>` prompt that does not come back means the paste was cut off: Ctrl+C, paste again.
4. `bash setup_textract.sh you@yourdomain.com` -- the email gets the budget alerts. It ends
   by printing the two key lines once. Then step 3 of the section above.

## Checks the narrow key cannot make

The laptop key is denied everything outside Textract and its budget, by design -- including
reading the budget's cut-off action. To see the action is armed, in CloudShell:

    aws budgets describe-budget-actions-for-budget \
      --account-id "$(aws sts get-caller-identity --query Account --output text)" \
      --budget-name lunenburg-textract \
      --query 'Actions[].[ActionThreshold.ActionThresholdValue,ApprovalModel,Status]' --output text

Expected: `100.0  AUTOMATIC  STANDBY`. `EXECUTION_SUCCESS` means it has fired and the user is
denied: detach the policy (Budgets console, the action's "Reverse" button) only after reading why.

## Day to day

    python3 scripts/textract_pages.py FILE --pages 22,26,41 --dry-run   # what it would send, and cost
    python3 scripts/textract_pages.py FILE --pages 22,26,41             # send it
    python3 scripts/textract_spend.py --status                          # 24 hours, month, AWS, latch

The ingestion dashboard (`bash scripts/status.sh`) carries a Textract card: running or idle,
the run's progress and ceiling, the last 24 hours, the month against the cap, AWS's figure and
its age, and the latch. If it shows **CUT OFF**, read `build/STOP-TEXTRACT`, then delete it.

## Facts this rests on, and where they came from

- Price: $0.015/page for TABLES, $0.0015/page for plain text, US East, first million pages a
  month. https://aws.amazon.com/textract/pricing/, read 27 October 2026.
- Size: a page sent as bytes must be under 5 MB (the API and boto3 references; the quotas page
  says 10 MB, unreconciled, so the lower) and under 10,000 pixels a side.
  https://docs.aws.amazon.com/textract/latest/dg/limits-document.html. None of the 2,751
  annual-report pages exceeded 5 MB; an oversized page falls back to a JPEG, 300 dpi down to
  150, and the output says which.
- First real run, 27 October 2026: FY2020 pp. 22, 26, 41 for $0.045. On p41 -- the rotated
  trust table 13b was written about -- every proven `stabilization-balances.csv` figure came
  back in its own row, ending cash always column 9 and ending market column 12. Three pages;
  the pilot against all 511 proven pages is what measures it.
