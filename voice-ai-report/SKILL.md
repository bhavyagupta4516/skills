---
name: voice-ai-report
description: |
  Generates three comprehensive Voice AI reports for SuperYou (D2C brand) from three CSV query exports:
  1. Executive performance PDF (KPIs, funnel, benchmarks, action plan — NO transcript details)
  2. Bot training report PDF (transcript-based insights, issues, fixes for development team)
  3. WhatsApp win message (short shareable update for stakeholders)
  
  Use this skill EVERY TIME the user uploads CSV files related to Voice AI, call transcripts, call metadata,
  or abandoned checkout recovery — even if they don't say "report". Triggers on phrases like:
  "analyse my voice AI", "generate voice AI report", "here are my call files", "create performance report",
  or whenever 3 CSV files are uploaded that contain call/transcript/order data.
  
  The skill reads three CSVs (transcripts, call metadata, orders/conversions), computes all KPIs,
  classifies call outcomes, and generates three output files ready to download and share.
---

# Voice AI Performance Report — SuperYou

## What this skill does

Reads three CSV exports from the LimeChat/Voice AI platform and produces three ready-to-share outputs:

### 1. Executive Performance PDF
- Volume & reach metrics
- Conversion funnel (calls → engaged → link sent → orders)
- Call outcome breakdown (classified from AI summaries)
- Call duration distribution
- Industry benchmark comparison
- Prioritised action plan with expected uplift
- **NO transcript details — safe for external stakeholders**

### 2. Bot Training Report PDF
- Detailed transcript-driven insights (all 12 issue categories)
- Specific examples from actual calls
- Recommended prompts and handling scripts for each issue
- Language-specific recommendations
- Competitor comparison findings
- **For development/ops team to improve bot performance**

### 3. WhatsApp Win Message
- Two versions: punchy celebratory + professional update
- Ready to copy/paste to team or stakeholders
- Includes key numbers and next steps

---

## Input files

The user uploads exactly 3 CSV files. Identify which is which by their columns:

| File role | Key columns |
|---|---|
| **Transcripts** | `user_id`, `agent_name`, `turns`, `full_transcription`, `ai_summary` |
| **Call metadata** | `user_id`, `call_id`, `duration_seconds`, `call_ended_by`, `user_spoke`, `call_handoff_initiated_at`, `tools_called`, `failure_reason` |
| **Orders / conversions** | `amount`, `order_id`, `interaction_type`, `phone_number`, `name` |

Do NOT assume file order — always detect by column names.

---

## Step 1: Read all three files

```python
import pandas as pd

files = [
    "/mnt/user-data/uploads/<file1>.csv",
    "/mnt/user-data/uploads/<file2>.csv",
    "/mnt/user-data/uploads/<file3>.csv",
]

dfs = {}
for f in files:
    df = pd.read_csv(f)
    cols = set(df.columns)
    if 'ai_summary' in cols:
        dfs['transcripts'] = df
    elif 'duration_seconds' in cols:
        dfs['calls'] = df
    elif 'order_id' in cols or 'amount' in cols:
        dfs['orders'] = df

df_t = dfs['transcripts']   # 174 rows typical
df_c = dfs['calls']          # 110 rows typical
df_o = dfs.get('orders', pd.DataFrame())
```

---

## Step 2: Compute metrics

### Call metrics (from calls file)
```python
total_calls      = len(df_c)
user_spoke       = int(df_c['user_spoke'].sum())
bot_ended        = int((df_c['call_ended_by'] == 'bot').sum())
customer_ended   = int((df_c['call_ended_by'] == 'customer').sum())
handoffs         = int(df_c['call_handoff_initiated_at'].notna().sum())
avg_duration     = df_c['duration_seconds'].mean()
median_duration  = df_c['duration_seconds'].median()

bins   = [0, 10, 30, 60, 120, 300, 10000]
labels = ['<10s', '10–30s', '30–60s', '60–120s', '120–300s', '300s+']
df_c['dur_bucket'] = pd.cut(df_c['duration_seconds'], bins=bins, labels=labels)
dur_dist = df_c['dur_bucket'].value_counts().sort_index().to_dict()
```

### Order / conversion metrics (from orders file)
```python
total_orders = len(df_o)
total_gmv    = float(df_o['amount'].sum()) if not df_o.empty else 0
avg_order    = float(df_o['amount'].mean()) if not df_o.empty else 0
```

### Outcome classification (from transcripts file)
Classify each `ai_summary` string into one of these buckets:

```python
def classify_outcome(summary):
    if not isinstance(summary, str):
        return 'no_transcript'
    s = summary.lower()
    if ('voicemail' in s and
            ('forwarded' in s or 'reached' in s or 'attempted' in s)):
        return 'voicemail'
    if ('confirmed they were not' in s or 'apologized for the mistake' in s
            or ('reached' in s and 'instead' in s)):
        return 'wrong_number'
    if ('already' in s and
            ('ordered' in s or 'bought' in s or 'completed' in s or 'placed' in s)):
        return 'already_ordered'
    if (('checkout link' in s or 'whatsapp' in s) and
            ('sent' in s or 'send' in s or 'offered' in s or
             'accepted' in s or 'agreed' in s)):
        return 'link_sent'
    if ('confirmed she would proceed' in s or 'confirmed they plan' in s
            or 'plan to complete' in s or 'intent to place' in s):
        return 'committed_later'
    if 'not interested' in s or 'declined' in s or 'did not wish to purchase' in s:
        return 'declined'
    if ('too expensive' in s or
            ('price' in s and ('high' in s or 'concern' in s))):
        return 'price_objection'
    if ('busy' in s or 'not available' in s
            or 'unable to talk' in s or 'not able to talk' in s):
        return 'busy'
    if ('language' in s or 'spanish' in s or 'gujarati' in s
            or 'kannada' in s or 'barrier' in s):
        return 'language_barrier'
    if 'screening' in s or ('record' in s and 'name' in s):
        return 'call_screening'
    if 'privacy' in s or 'number was obtained' in s:
        return 'privacy_concern'
    if 'cash on delivery' in s or ('cod' in s and 'not' in s):
        return 'cod_issue'
    if 'audio' in s or 'quality' in s or 'clarity' in s:
        return 'call_quality'
    if ('no further' in s and ('conversation' in s or 'action' in s)) or \
       ('greeting' in s and ('no further' in s or 'did not progress' in s)) or \
       ('did not progress' in s) or \
       ('only' in s and 'greeting' in s):
        return 'short_call'
    return 'engaged_partial'

df_t['outcome'] = df_t['ai_summary'].apply(classify_outcome)
outcome_counts = df_t['outcome'].value_counts().to_dict()
```

### Derived rates
```python
meaningful_outcomes = [
    'link_sent', 'committed_later', 'declined', 'price_objection',
    'busy', 'already_ordered', 'cod_issue', 'engaged_partial', 'call_quality'
]
meaningful_n     = df_t[df_t['outcome'].isin(meaningful_outcomes)].shape[0]
engagement_rate  = meaningful_n / len(df_t) * 100
link_sent_n      = outcome_counts.get('link_sent', 0)
link_sent_rate   = link_sent_n / len(df_t) * 100
link_to_order    = (total_orders / link_sent_n * 100) if link_sent_n > 0 else 0
short_call_n     = outcome_counts.get('short_call', 0)
voicemail_n      = outcome_counts.get('voicemail', 0)
under_30s        = (dur_dist.get('<10s', 0) + dur_dist.get('10–30s', 0))
under_30s_pct    = under_30s / total_calls * 100
```

---

## Step 3: Scan all ai_summaries for issues

Look for these specific patterns across all transcripts and count occurrences:

| Issue key | Detection pattern |
|---|---|
| `language_barrier` | Hindi/Gujarati/Kannada/Spanish in summary |
| `voicemail_confusion` | Bot asking hello repeatedly to voicemail |
| `wrong_number` | Identity mismatch / wrong person reached |
| `discount_objection` | User asked for coupon/discount, bot had none |
| `delivery_query` | User asked about delivery timelines / pincode |
| `cod_issue` | Cash-on-delivery not available |
| `call_screening` | IVR / name-recording system blocked the call |
| `call_quality` | Audio clarity issues mentioned |
| `already_purchased` | Customer had already bought items |
| `no_escalation` | Complex objection with no human handoff |
| `product_knowledge_gap` | Bot couldn't answer product/price question |
| `privacy_concern` | User asked how their number was obtained |

---

## Step 4: Generate three output PDFs

### Output 1: Executive Performance PDF (SuperYou_VoiceAI_Report.pdf)
Use ReportLab to create a professional PDF with:
- Navy/blue header with SuperYou branding
- Metric cards: total calls, user spoke %, avg duration, handoffs, orders recovered
- Conversion funnel chart (calls → user spoke → engagement → link sent → orders)
- Two side-by-side bar charts: call outcome breakdown + duration distribution
- Industry benchmark table (link-to-order rate, engagement rate, avg duration, voicemail rate, AOV, escalation rate)
- Priority action plan (4-quadrant grid: do this week / next sprint / medium term / expected uplift)
- NO transcript content, no issue details — executive summary only

### Output 2: Bot Training Report PDF (SuperYou_VoiceAI_Training_Insights.pdf)
Use ReportLab to create a detailed training guide with:
- Volume summary (total calls, transcripts, conversion numbers)
- Issue analysis grid — for EACH detected issue:
  - Title and issue category
  - **Transcript excerpts** (2–3 direct quotes from ai_summary showing the problem)
  - Root cause analysis
  - Recommended bot response / prompt
  - Competitor positioning (if relevant)
  - Example handling script
  
Example issue card:
```
Language Barrier (5 calls detected)
─────────────────────────────────
Transcript evidence:
• "The user responded in Hindi and the agent struggled to keep up"
• "Customers spoke Gujarati, Kannada — bot defaulted to English causing drop-off"

Root cause: Bot lacks regional language support. No fallback to Hindi/Gujarati/Kannada.

Recommended bot prompt:
"Hello! I can help you in English or Hindi. Which would you prefer?"

Expected outcome: +15–20% engagement in regional markets

Training note: Enable voice language detection on call initiate. Route Hindi calls to 
Meera's Hindi variant model. Test with 10 calls before scaling.
```

Include sections for:
- Multi-language failure
- Voicemail confusion
- Wrong number / identity mismatch
- Discount / coupon objection (with sample discount offer flow)
- Delivery / pincode queries (with API integration notes)
- Cash-on-delivery not offered
- Call screening / IVR blocks
- Call quality / audio issues
- Already purchased / false trigger
- No human escalation path
- Partial product knowledge (with product KB gaps to fill)
- Privacy / consent concern

### Output 3: WhatsApp Win Message (as plain text file)
Create a simple text file with two message variants (copy-paste ready):

**Variant 1 — Punchy & Celebratory:**
```
🎉 Voice AI update for SuperYou!

Meera made 110 calls in just 2 days and here's what happened 👇

📞 91% of customers picked up & spoke
🔗 37 checkout links sent
✅ 5 orders recovered
💰 ₹15,649 GMV — avg order ₹3,130

And we're just getting started. With a few fixes (Hindi support, voicemail detection, discount flows) we're projecting ₹35–45K GMV per 100 calls 🚀

Voice AI is live and converting. Let's scale! 💪
```

**Variant 2 — Professional Update:**
```
📊 SuperYou Voice AI — 2-Day Performance Snapshot

Agent Meera ran 110 abandoned checkout recovery calls (May 26–27).

Key numbers:
• 91% connect rate
• 37 checkout links delivered
• 5 orders confirmed · ₹15,649 recovered
• Avg order value: ₹3,130 (above D2C benchmark)

Opportunity: engagement rate and call duration are below industry avg. With Hindi language support, voicemail detection, and a discount objection flow, we project GMV can 2–3x per batch.

Full report attached. Happy to walk through the fixes. 🙏
```

---

## Step 5: Output files summary (in chat)

After generating all three files, post in chat:
- ✅ Executive Performance PDF generated
- ✅ Bot Training Report PDF generated  
- ✅ WhatsApp messages ready
- Brief summary of key findings (2–3 bullets)
- Offer to customize any of the outputs or discuss next steps

---

## Industry benchmark reference (for Executive PDF)

Use these values in the benchmark comparison table:

```
link_to_order_industry:   "8–15%"
engagement_rate_industry: "40–55%"
avg_duration_industry:    "90–120s"
voicemail_rate_industry:  "20–35%"
avg_order_value_industry: "₹1,500–₹2,500"
escalation_rate_industry: "10–20%"
```

---

## Transcript issue categories (for Bot Training PDF)

These 12 issues must be scanned and extracted with supporting quotes:

| Issue | Detection pattern |
|---|---|
| Multi-language failure | Hindi/Gujarati/Kannada/Spanish mentioned; user language mismatch |
| Voicemail confusion | "hello?" repeated; bot unable to detect voicemail |
| Wrong number / identity | User confirmed not the intended person; agent apologised |
| Discount / coupon objection | User asked for discount/coupon; bot had no offer |
| Delivery / pincode queries | User asked about delivery timeline; bot couldn't check pincode |
| Cash-on-delivery not offered | User stated COD not available; dropped call |
| Call screening / IVR blocks | System requested name/reason; bot couldn't navigate |
| Call quality / audio issues | User mentioned clarity problems; asked for callback |
| Already purchased / false trigger | User stated already ordered elsewhere or from SuperYou |
| No human escalation path | Complex objection; bot ended call instead of escalating |
| Partial product knowledge | Bot couldn't quote SKU pricing; lacked competitor comparison |
| Privacy / consent concern | User asked how number was obtained; requested opt-out |

For each detected issue:
- **Count occurrences** in the transcript file (group by outcome classification)
- **Extract 2–3 direct quotes** from ai_summary field that evidence the issue
- **Determine impact**: How many calls were lost to this issue?
- **Write recommendation**: What prompt/logic should the bot use instead?

---

## Notes

- All currency is INR (₹)
- Agent name is "Meera" (SuperYou ABC agent)
- Campaign type is "Abandoned checkout recovery" (telephony channel)
- Executive PDF = shareable with stakeholders, clients, investors (zero transcript content)
- Training PDF = internal team use only (contains specific call insights for bot improvement)
- WhatsApp messages = copy-paste ready for team comms or social sharing
- If the orders file is empty or missing, show 0 conversions and note data may not be available yet
- Duration bucket labels: `<10s`, `10–30s`, `30–60s`, `60–120s`, `120–300s`, `300s+`
- Funnel engagement % = meaningful outcomes / total transcripts × 100
- Link sent rate = link_sent outcomes / total transcripts × 100
