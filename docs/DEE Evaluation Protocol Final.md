# DEE Evaluation Protocol Final

> This frozen protocol adopts Report A as the evaluator specification and uses Report B only for the Track A / Track B reporting and reviewer-defense framing.  

## 1. Scope

This protocol defines the final evaluation system for Chinese financial document-level event extraction over the following datasets:

* **DuEE-Fin**
* **ChFinAnn**
* **DocFEE**

It applies to all model families that output structured event records, including:

* pipeline extractors;
* classification-and-filling systems;
* graph-based DEE systems;
* encoder-decoder generative systems;
* LLM-based structured extraction systems.

The evaluated task is **document-level event record extraction**. A model must predict, for each document, zero or more event records. Each record contains:

* a legal event type;
* a set of schema-defined roles;
* one or more textual values for each role.

This protocol evaluates **event records after event-type-constrained record alignment** and then computes **role-value-level strict micro-F1**.

It is a frozen benchmark protocol, not a discussion draft. Evaluator implementations must follow this document exactly.

## 2. Metric Stack

The benchmark uses a dual-track reporting system.

### Track A: Dataset-Official Metrics

Dataset-official metrics are mandatory comparability metrics. They preserve fair comparison with historical baselines.

| Dataset  | Official Metric Policy                                                                            | Purpose                  |
| -------- | ------------------------------------------------------------------------------------------------- | ------------------------ |
| DuEE-Fin | Online official score if available; otherwise clearly labeled offline official-style reproduction | Historical comparability |
| ChFinAnn | Doc2EDAG / ChFinAnn official greedy evaluator                                                     | Historical comparability |
| DocFEE   | DocFEE official evaluator                                                                         | Historical comparability |

Official metrics must be reported in the main table whenever available.

### Track B: Unified Strict Metric

The unified strict metric is the main scientific metric of this protocol:

**Unified Strict Role-Value Micro-F1 under Event-Type-Constrained Hungarian Matching**

It provides one consistent evaluator across DuEE-Fin, ChFinAnn, and DocFEE.

### Auxiliary Metrics

Auxiliary metrics are allowed only for analysis, not for main ranking:

* Auxiliary Normalized Role-Value Micro-F1
* Normalization sensitivity delta
* Official greedy vs Hungarian sensitivity analysis

### Diagnostic Metrics

Diagnostic metrics explain system behavior but are not main metrics:

* Record EM
* Per-event-type P/R/F1
* Event Type F1
* Single-record subset F1
* Multi-record subset F1
* Long-document subset F1
* Cross-sentence subset F1
* JSON validity
* Format validity
* Schema validity
* Invalid event type rate
* Invalid role rate
* Duplicate record rate
* Empty prediction rate

### Rejected Metrics

The following are rejected from automatic benchmark scoring:

* Semantic Equivalence F1
* LLM judge score
* Embedding similarity score
* Fuzzy string matching score
* Edit-distance matching score
* External-KB alias-normalized score
* Gold-repaired score
* Schema-guessed score
* Role-guessed score
* Event-type-guessed score
* Offset F1 as a main metric

Offset F1 may only be used as an optional span-submodule diagnostic for systems that explicitly output offsets.

## 3. Main Metric Definition

The final main scientific metric is:

**Unified Strict Role-Value Micro-F1 under Event-Type-Constrained Hungarian Matching**

### 3.1 Grouping

For each dataset split, document `d`, and legal event type `t`, construct:

[
G_{d,t} = {g_1, g_2, ..., g_m}
]

[
P_{d,t} = {p_1, p_2, ..., p_n}
]

where:

* (G_{d,t}) is the gold record set for document `d` and event type `t`;
* (P_{d,t}) is the predicted record set for document `d` and event type `t`;
* matching is performed only inside the same `(document_id, event_type)` group.

No cross-event-type matching is allowed.

### 3.2 Record Representation

After validation and strict normalization, each record is represented as:

```python
{
  "event_type": t,
  "roles_to_values": {
    role_name: frozenset(normalized_string_values)
  }
}
```

Rules:

* `null`, empty strings, and empty lists are ignored for scoring.
* Multi-value roles are represented as unordered sets.
* Value order does not affect scoring.
* Duplicate values within the same role are collapsed for scoring but logged separately.
* Duplicate records are not collapsed.

### 3.3 Pair Score

For a predicted record (p) and a gold record (g) in the same `(document_id, event_type)` group, define:

[
s(p,g)=|{r \mid r \in roles(p) \cap roles(g),\ p[r] = g[r]}|
]

That is, the pair score is the number of roles whose normalized value sets are exactly equal.

No semantic similarity, edit distance, embedding similarity, LLM judge, date conversion, amount conversion, or alias expansion may be used in the pair score.

### 3.4 Matching

For each `(document_id, event_type)` group:

1. Build a bipartite graph between predicted records and gold records.
2. Use pair score (s(p,g)) as edge weight.
3. Pad the matrix with dummy rows or columns when the two sides have unequal size.
4. Use Hungarian matching to maximize total pair score.
5. Treat any real pred-gold assignment with score `0` as unmatched.

The implementation must be deterministic. Dependency versions and matching configuration must be recorded.

### 3.5 TP / FP / FN

For each matched pair `(p, g)` with pair score greater than zero, compute role-value TP / FP / FN over all schema-defined roles for that event type.

For each role `r`:

* If both prediction and gold have no value: no count.
* If prediction and gold have identical value sets:
  `TP += |V_g|`
* If gold has values but prediction has none:
  `FN += |V_g|`
* If prediction has values but gold has none:
  `FP += |V_p|`
* If both have values but value sets differ:
  `FP += |V_p|`
  `FN += |V_g|`

For unmatched predicted records:

* all non-empty legal role values count as FP.

For unmatched gold records:

* all non-empty gold role values count as FN.

Illegal event types and illegal roles are handled as defined in Sections 6 and 8.

### 3.6 Micro Aggregation

Aggregate TP, FP, and FN over all documents, event types, records, roles, and values:

[
P=\frac{TP}{TP+FP}
]

[
R=\frac{TP}{TP+FN}
]

[
F_1=\frac{2PR}{P+R}
]

If both numerator and denominator are zero, precision, recall, and F1 are defined as `0.0` unless explicitly specified in a unit test.

Macro-F1 is not a main metric.

## 4. Dataset-Specific Protocol

### 4.1 DuEE-Fin

DuEE-Fin must be reported with two separated tracks when possible.

#### Track A: Official / Official-Style

Preferred:

* report the official online score from the official evaluation platform;
* record the submission date;
* do not alter official evaluator behavior.

If online official evaluation is unavailable:

* report an **Offline Official-Style** score;
* clearly label it as offline reproduction;
* publish the reproduction evaluator, version, commit hash, and command line;
* never mix offline dev scores with hidden-test leaderboard scores.

Required wording:

> DuEE-Fin official test evaluation is not fully reproducible offline in this setting. When online submission is available, we report the official online score. Otherwise, we report an offline official-style reproduction and mark it separately from official hidden-test leaderboard results.

#### Track B: Unified Strict

Always report:

* DuEE-Fin Unified Strict P/R/F1;
* evaluator version;
* schema version;
* split version;
* normalization config hash;
* matching config hash.

All model selection, parser updates, normalization decisions, and threshold decisions must be frozen on the development set before test evaluation.

### 4.2 ChFinAnn

#### Track A: Official

ChFinAnn official scores must be computed using the official Doc2EDAG / ChFinAnn evaluator or an explicitly pinned official implementation.

The official greedy matcher must be preserved.

Historical baselines such as Doc2EDAG, GIT, DE-PPN, and IPGPF must be compared under the official metric unless their prediction files are re-evaluated with the unified evaluator.

#### Track B: Unified Strict

Report:

* ChFinAnn Unified Strict P/R/F1;
* Hungarian matching;
* strict role-value matching;
* no cross-event-type matching.

The unified score must not replace the official score. It is a separate scientific metric.

### 4.3 DocFEE

#### Track A: Official

Use the DocFEE official evaluator and lock:

* repository commit;
* evaluator version;
* schema version;
* split version;
* command line.

Official DocFEE constraints must be followed in the official metric.

#### Track B: Unified Strict

Report:

* DocFEE Unified Strict P/R/F1;
* JSON validity;
* schema validity;
* invalid event type rate;
* invalid role rate;
* duplicate record rate;
* empty output rate.

For the unified strict metric, the evaluator must not repair generative outputs. It only parses, validates, normalizes under the strict policy, matches, and scores.

`value-in-source` checks are not part of the unified strict main metric unless required by the dataset-official evaluator. They may be logged as diagnostics for DocFEE analysis.

## 5. Canonical Prediction Schema

Predictions must be submitted as JSONL, one document per line.

### 5.1 Prediction Example

```json
{
  "document_id": "doc_001",
  "predictions": [
    {
      "event_type": "股东减持",
      "event_id": "optional_not_scored",
      "arguments": {
        "减持股东": ["张三", "李四"],
        "减持金额": "1,000万元",
        "减持日期": null
      }
    }
  ]
}
```

### 5.2 Gold Example

Gold records must be convertible to the same canonical structure:

```json
{
  "document_id": "doc_001",
  "gold_events": [
    {
      "event_type": "股东减持",
      "event_id": "gold_optional_not_scored",
      "arguments": {
        "减持股东": ["张三", "李四"],
        "减持金额": "1000万元"
      }
    }
  ]
}
```

### 5.3 Field Rules

| Field         | Required | Type                          |            Scored |
| ------------- | -------: | ----------------------------- | ----------------: |
| `document_id` |      Yes | string                        | Used for grouping |
| `predictions` |      Yes | list                          |         Container |
| `event_type`  |      Yes | string                        |               Yes |
| `event_id`    |       No | string                        |                No |
| `arguments`   |      Yes | object                        |         Container |
| role key      |      Yes | string                        |               Yes |
| role value    |      Yes | string, list[string], or null |  Yes if non-empty |

### 5.4 Value Rules

Allowed:

```json
"减持金额": "1000万元"
```

```json
"减持股东": ["张三", "李四"]
```

```json
"减持日期": null
```

Invalid:

```json
"减持金额": 1000
```

```json
"减持股东": {"name": "张三"}
```

```json
"减持日期": ["2024年1月1日", 20240101]
```

Invalid values must be logged and handled according to Section 6.

## 6. Validation Rules

### 6.1 JSON Validation

The evaluator must validate:

1. each JSONL line is parseable JSON;
2. each parsed object contains `document_id`;
3. `document_id` is a string;
4. `predictions` exists and is a list;
5. each prediction record is an object;
6. each prediction record contains `event_type`;
7. `event_type` is a string;
8. `arguments` exists and is an object.

If an entire document line cannot be parsed:

* the document is treated as having empty predictions;
* all corresponding gold records become unmatched;
* JSON validity decreases;
* the raw line is logged.

If one record inside a parseable document is invalid:

* that record is discarded if it cannot be canonicalized;
* other records in the document continue to be scored;
* format validity decreases;
* the invalid record is logged.

### 6.2 Event Type Validation

For each prediction record:

* if `event_type` is legal for the dataset schema, the record proceeds to role validation;
* if `event_type` is illegal, the entire record is invalid for matching.

Illegal event type handling:

* no matching against any gold event type;
* all non-empty argument values count as FP;
* the case is logged in `invalid_cases.csv`;
* invalid event type rate increases.

The evaluator must not map an illegal event type to a similar legal event type.

### 6.3 Role Validation

For each legal event type:

* every role key must belong to the schema of that event type;
* legal roles proceed to value validation;
* illegal roles are removed from matching but still counted as FP.

Illegal role handling:

* all non-empty values under the illegal role count as FP;
* the legal part of the record remains eligible for matching;
* the case is logged;
* invalid role rate increases.

The evaluator must not silently drop illegal roles.

### 6.4 Value Validation

Allowed value types:

* `string`
* `list[string]`
* `null`

Handling:

* `null` is ignored for scoring;
* empty string after stripping is ignored but logged as empty value;
* list order does not affect scoring;
* duplicate values inside a list are collapsed for scoring but logged;
* numbers, objects, nested arrays, booleans, and mixed-type lists are invalid.

Invalid value handling:

* invalid values are not used in matching;
* if attached to a legal role, they count as FP when recoverable as non-empty raw output;
* they are logged in `invalid_cases.csv`.

## 7. Matching Algorithm

### 7.1 Grouping

The evaluator groups records by:

```text
(dataset, split, document_id, event_type)
```

Only records in the same group are eligible for matching.

### 7.2 Pair Score

For every predicted record `p` and gold record `g` in the same group:

```text
pair_score(p, g) =
number of schema roles r such that normalized_value_set(p, r)
equals normalized_value_set(g, r)
```

A role contributes `1` to the pair score only when the full value set for that role is exactly equal.

Partial overlap inside a multi-value role does not contribute to the pair score.

### 7.3 Hungarian Matching

For each group:

1. construct an `n × m` score matrix;
2. pad with dummy rows or columns if needed;
3. run Hungarian matching to maximize total score;
4. discard dummy matches;
5. discard real pred-gold matches with score `0`.

Implementation requirement:

```python
scipy.optimize.linear_sum_assignment
```

or an equivalent deterministic implementation with identical regression outputs.

### 7.4 Tie-Breaking

When multiple optimal matchings have identical total pair score, the evaluator must break ties deterministically.

Tie-breaking order:

1. maximize total pair score;
2. maximize total number of exactly matched role-value atoms after the matching;
3. minimize total FP + FN under the matching;
4. minimize the lexicographic list of `(pred_index, gold_index)` pairs;
5. record dependency version and matching config hash.

The same input must produce identical matching logs across repeated runs.

### 7.5 Unmatched Handling

Unmatched predicted record:

* every non-empty legal role value counts as FP.

Unmatched gold record:

* every non-empty gold role value counts as FN.

Zero-score pred-gold assignment:

* treated as unmatched pred plus unmatched gold.

### 7.6 Duplicate Handling

Duplicate records are not removed.

If two identical predicted records correspond to one gold record:

* at most one prediction can match the gold record;
* remaining duplicates are unmatched;
* all their non-empty legal role values count as FP;
* duplicate record rate is reported.

### 7.7 Cross-Type Errors

If the gold event type is `A` and the prediction uses event type `B`:

* the prediction is evaluated only in group `B`;
* the gold record remains unmatched in group `A`;
* no cross-type rescue is allowed.

## 8. TP / FP / FN Rules

### 8.1 Matched Record Pair

For each matched `(p, g)` and each schema role `r`:

Let:

```text
Vp = normalized value set predicted for role r
Vg = normalized gold value set for role r
```

Rules:

| Case                      | Count    |    |           |    |   |
| ------------------------- | -------- | -- | --------- | -- | - |
| `Vp = ∅`, `Vg = ∅`        | no count |    |           |    |   |
| `Vp = Vg`, non-empty      | `TP +=   | Vg | `         |    |   |
| `Vp = ∅`, `Vg ≠ ∅`        | `FN +=   | Vg | `         |    |   |
| `Vp ≠ ∅`, `Vg = ∅`        | `FP +=   | Vp | `         |    |   |
| `Vp ≠ Vg`, both non-empty | `FP +=   | Vp | `, `FN += | Vg | ` |

### 8.2 Multi-Value Role

Gold:

```json
"减持股东": ["张三", "李四"]
```

Prediction:

```json
"减持股东": ["李四", "张三"]
```

Result:

```text
TP += 2
```

Gold:

```json
"减持股东": ["张三", "李四"]
```

Prediction:

```json
"减持股东": ["张三"]
```

Result:

```text
FP += 1
FN += 2
```

Partial multi-value overlap is not treated as partial TP under the strict metric.

### 8.3 Unmatched Prediction

Prediction:

```json
{
  "event_type": "股东减持",
  "arguments": {
    "减持股东": ["张三"],
    "减持金额": "1000万元"
  }
}
```

If unmatched:

```text
FP += 2
```

### 8.4 Unmatched Gold

Gold:

```json
{
  "event_type": "股东减持",
  "arguments": {
    "减持股东": ["张三"],
    "减持金额": "1000万元"
  }
}
```

If unmatched:

```text
FN += 2
```

### 8.5 Illegal Event Type

Prediction with illegal event type:

```json
{
  "event_type": "股东减持事件",
  "arguments": {
    "减持股东": ["张三"],
    "减持金额": "1000万元"
  }
}
```

Result:

```text
FP += 2
invalid_event_type += 1
```

No matching is attempted.

### 8.6 Illegal Role

Prediction:

```json
{
  "event_type": "股东减持",
  "arguments": {
    "减持股东": ["张三"],
    "错误角色": "1000万元"
  }
}
```

Result:

```text
"错误角色" value counts as FP
"减持股东" remains eligible for matching
invalid_role += 1
```

### 8.7 Empty Cases

| Gold      | Prediction | Result                           |
| --------- | ---------- | -------------------------------- |
| non-empty | empty      | all gold values count as FN      |
| empty     | non-empty  | all predicted values count as FP |
| empty     | empty      | no TP, FP, FN                    |

True negatives are never counted.

## 9. Normalization Policy

### 9.1 Strict Metric Allowed Normalization

Only the following operations are allowed before unified strict matching:

1. Unicode NFKC normalization.
2. Full-width ASCII to half-width ASCII.
3. Strip leading and trailing whitespace.
4. Collapse consecutive whitespace into a single space.
5. Normalize listed punctuation variants:

   * Chinese parentheses to ASCII parentheses;
   * Chinese comma to ASCII comma;
   * Chinese semicolon to ASCII semicolon;
   * Chinese colon to ASCII colon;
   * Chinese quotation marks to ASCII quotation marks;
   * Chinese single quotation marks to ASCII apostrophes.
6. Remove thousands separators inside digit sequences:

   * `1,234` → `1234`
7. Remove zero-width and invisible control characters.

These operations must be deterministic and logged when they change a value.

### 9.2 Auxiliary-Only Normalization

The following operations are allowed only for the auxiliary normalized metric:

1. date format standardization;
2. explicit amount unit conversion;
3. percentage formatting normalization beyond NFKC;
4. document-internal explicit alias normalization;
5. company short-name / full-name mapping with a fixed whitelist;
6. stock-code / company-name mapping only if provided by gold metadata or fixed dataset schema.

Auxiliary normalized scores must never replace unified strict scores.

### 9.3 Forbidden Normalization

The following are forbidden in automatic scoring:

* external knowledge-base alias expansion;
* LLM-based equivalence judgment;
* embedding similarity matching;
* edit-distance fuzzy matching;
* automatic date inference;
* automatic amount completion;
* automatic unit completion;
* company-name completion;
* role-name correction;
* event-type correction;
* schema guessing;
* coreference-based value repair;
* splitting `"张三、李四"` into `["张三", "李四"]`;
* repairing gold data during evaluation;
* adding new normalization rules after inspecting test results.

## 10. Output Report Fields

The evaluator must produce machine-readable outputs.

### 10.1 `overall_metrics.json`

Required fields:

```json
{
  "dataset": "ChFinAnn",
  "split": "test",
  "evaluator_version": "dee-eval-v1.0.0",
  "schema_version": "schema-v1",
  "schema_hash": "sha256:...",
  "split_version": "official",
  "normalization_config_hash": "sha256:...",
  "matching_config_hash": "sha256:...",
  "official": {
    "available": true,
    "metric_name": "Official F1",
    "evaluator": "official",
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  },
  "unified_strict": {
    "tp": 0,
    "fp": 0,
    "fn": 0,
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  },
  "aux_normalized": {
    "enabled": false,
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  },
  "diagnostics": {
    "record_em": 0.0,
    "event_type_f1": 0.0,
    "json_validity": 0.0,
    "format_validity": 0.0,
    "schema_validity": 0.0,
    "invalid_event_type_rate": 0.0,
    "invalid_role_rate": 0.0,
    "duplicate_record_rate": 0.0,
    "empty_prediction_rate": 0.0
  }
}
```

### 10.2 Required Logs

The evaluator must output:

| File                    | Required Content                                                                                   |
| ----------------------- | -------------------------------------------------------------------------------------------------- |
| `matching_log.csv`      | `document_id`, `event_type`, `pred_idx`, `gold_idx`, `pair_score`, `matched`, `matched_roles`      |
| `unmatched_cases.csv`   | unmatched predicted and gold records                                                               |
| `error_cases.csv`       | FP atoms, FN atoms, mismatch reason                                                                |
| `invalid_cases.csv`     | invalid JSON, invalid event type, invalid role, invalid value type                                 |
| `normalization_log.csv` | raw value, normalized value, applied rule                                                          |
| `duplicate_log.csv`     | duplicate records and duplicate role values                                                        |
| `config.json`           | schema version, split version, normalizer config, matcher config, dependency versions, commit hash |

## 11. Required Test Suite

The evaluator is not frozen unless all tests pass.

| Test ID | Test Name                         | Scenario                                                     | Expected Behavior                                                            |
| ------- | --------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| T01     | Gold vs Gold                      | Prediction equals gold                                       | Official and unified strict P/R/F1 = 1.0                                     |
| T02     | Empty Prediction                  | Gold non-empty, prediction empty                             | TP=0, FP=0, all gold values count as FN                                      |
| T03     | Empty Gold                        | Gold empty, prediction non-empty                             | TP=0, FN=0, all predicted values count as FP                                 |
| T04     | Empty Both                        | Gold empty, prediction empty                                 | No TP/FP/FN; no TN counted                                                   |
| T05     | Wrong Event Type                  | Gold type `A`, prediction type `B`                           | Prediction counts as FP under `B`; gold counts as FN under `A`               |
| T06     | Illegal Event Type                | Prediction type not in schema                                | Entire record counts as FP; no matching                                      |
| T07     | Illegal Role                      | Legal event type with non-schema role                        | Illegal role values count as FP; legal roles continue                        |
| T08     | Invalid JSON Line                 | One document line cannot parse                               | Document treated as empty prediction; JSON validity decreases                |
| T09     | Invalid Record                    | One record malformed inside valid document                   | Record discarded; other records continue                                     |
| T10     | Invalid Value Type                | Role value is number/object/nested list                      | Invalid value logged and not used for matching                               |
| T11     | Duplicate Prediction              | Two identical predictions, one gold record                   | One may match; duplicate counts as FP                                        |
| T12     | Partial Record                    | Some roles correct, some missing                             | Correct exact role values count as TP; missing gold values count as FN       |
| T13     | Wrong Role Value                  | Same role, different value                                   | Prediction value counts as FP; gold value counts as FN                       |
| T14     | Multi-Value Order                 | Gold `["A","B"]`, prediction `["B","A"]`                     | Exact set match; TP for both values                                          |
| T15     | Multi-Value Partial Overlap       | Gold `["A","B"]`, prediction `["A"]`                         | Strict mismatch; FP for prediction set, FN for gold set                      |
| T16     | Multiple Same-Type Records        | Two gold and two prediction records with crossing similarity | Hungarian finds globally optimal alignment                                   |
| T17     | Greedy vs Hungarian Difference    | Constructed order-sensitive case                             | Unified Hungarian score is deterministic and may differ from official greedy |
| T18     | Zero-Score Pair                   | Hungarian assigns score-0 real pair                          | Treated as unmatched pred plus unmatched gold                                |
| T19     | Strict Normalization              | Full-width digits, whitespace, punctuation, thousands comma  | Allowed strict normalization enables match                                   |
| T20     | Auxiliary Normalization Isolation | Date / amount / alias normalization                          | Only auxiliary score changes; unified strict unchanged                       |
| T21     | No Auto Split                     | Prediction `"张三、李四"` vs gold `["张三","李四"]`                   | No automatic split; strict mismatch                                          |
| T22     | No External Alias                 | Prediction company short name vs gold full name              | No match in strict metric                                                    |
| T23     | Tie-Breaking Determinism          | Same input run multiple times                                | Identical metrics and matching logs                                          |
| T24     | Official Adapter Regression       | ChFinAnn / DocFEE fixed sample                               | Official adapter matches official script output                              |
| T25     | Unified Regression                | Fixed toy cases                                              | TP/FP/FN/F1 match golden files exactly                                       |
| T26     | Config Hash Stability             | Same config and data                                         | Same schema, normalizer, matcher hashes                                      |
| T27     | Test-Time Mutation Guard          | Config changed after test run                                | Evaluator must report changed hash; result invalid for leaderboard           |
| T28     | Silent Drop Guard                 | Illegal roles exist                                          | Invalid role rate > 0 and FP counted                                         |
| T29     | Duplicate Value Log               | Same value repeated inside one role                          | Scoring uses set; duplicate logged                                           |
| T30     | Dataset Split Check               | Wrong split name or unknown document ID                      | Evaluator raises validation error or reports split mismatch                  |

## 12. Paper Reporting Template

### 12.1 Main Table

Use the following main table structure.

| Model      | DuEE-Fin Official / Offline Official-Style F1 | DuEE-Fin Unified Strict F1 | ChFinAnn Official F1 | ChFinAnn Unified Strict F1 | DocFEE Official F1 | DocFEE Unified Strict F1 | Avg Official | Avg Unified Strict |
| ---------- | --------------------------------------------: | -------------------------: | -------------------: | -------------------------: | -----------------: | -----------------------: | -----------: | -----------------: |
| Baseline 1 |                                               |                            |                      |                            |                    |                          |              |                    |
| Baseline 2 |                                               |                            |                      |                            |                    |                          |              |                    |
| Ours       |                                               |                            |                      |                            |                    |                          |              |                    |

Required caption wording:

> We report dataset-official metrics as Track A for historical comparability and Unified Strict Role-Value Micro-F1 as Track B for cross-dataset scientific comparison. Official and unified metrics are not interchangeable.

### 12.2 Appendix Table: Per-Event-Type F1

| Dataset | Model | Event Type | #Gold Records | #Pred Records | Unified Strict P | Unified Strict R | Unified Strict F1 |
| ------- | ----- | ---------- | ------------: | ------------: | ---------------: | ---------------: | ----------------: |

### 12.3 Appendix Table: Subset Analysis

| Dataset  | Model | Subset                   | #Docs | #Gold Records | Official F1 | Unified Strict F1 | Record EM |
| -------- | ----- | ------------------------ | ----: | ------------: | ----------: | ----------------: | --------: |
| ChFinAnn |       | Single-record docs       |       |               |             |                   |           |
| ChFinAnn |       | Multi-record docs        |       |               |             |                   |           |
| DocFEE   |       | Long documents           |       |               |             |                   |           |
| DocFEE   |       | Cross-sentence arguments |       |               |             |                   |           |

### 12.4 Appendix Table: Normalization Sensitivity

| Dataset | Model | Unified Strict F1 | Auxiliary Normalized F1 | ΔF1 | Main Gain Source                    |
| ------- | ----- | ----------------: | ----------------------: | --: | ----------------------------------- |
|         |       |                   |                         |     | date / amount / alias / punctuation |

### 12.5 Appendix Table: Generative Output Validity

| Dataset | Model | JSON Validity | Format Validity | Schema Validity | Invalid Event Type Rate | Invalid Role Rate | Empty Output Rate | Duplicate Rate |
| ------- | ----- | ------------: | --------------: | --------------: | ----------------------: | ----------------: | ----------------: | -------------: |

### 12.6 Metrics Paragraph for Paper

Recommended text:

> We evaluate document-level event extraction with a dual-track protocol. Track A reports each dataset’s official metric to preserve comparability with prior work. Track B reports Unified Strict Role-Value Micro-F1, our main scientific metric, which aligns records within each document and event type using deterministic Hungarian matching and then computes strict role-value-level micro-F1. The unified metric uses only minimal deterministic character normalization and forbids semantic equivalence, LLM judging, schema guessing, role guessing, event-type guessing, and gold repair.

## 13. Reproducibility Checklist

Every reported result must include the following.

### Data

* Dataset name
* Dataset version
* Source URL or release identifier
* Train/dev/test split identifier
* Number of documents per split
* Number of event types
* Number of roles
* Number of gold records
* Hidden-test status, if applicable

### Schema

* Schema file path
* Schema version
* Schema hash
* Event type list
* Role list per event type

### Evaluator

* Evaluator version
* Evaluator commit hash
* Official evaluator commit hash where applicable
* Unified evaluator commit hash
* Dependency versions
* Python version
* `scipy` version
* OS / environment information

### Configuration

* Strict normalizer config
* Auxiliary normalizer config, if used
* Matching config
* Tie-breaking config
* Official adapter config
* Dataset adapter config

### Model / Prediction

* Model name
* Model checkpoint
* Prediction file path
* Prediction file hash
* Decoding config
* Random seed
* Prompt template version, if generative
* Parser version, if generative

### Command Line

Record exact commands, for example:

```bash
python eval_unified_dee.py \
  --dataset ChFinAnn \
  --split test \
  --schema schemas/chfinann_v1.json \
  --gold data/chfinann/test.gold.jsonl \
  --pred outputs/model.pred.jsonl \
  --strict-normalizer configs/strict_normalizer_v1.json \
  --matcher configs/hungarian_matcher_v1.json \
  --output-dir results/chfinann/model/
```

### Dev/Test Protocol

Required:

1. Use dev set for model selection.
2. Use dev set for parser debugging.
3. Use dev set for threshold selection.
4. Use dev set for normalization rule freezing.
5. Freeze evaluator code before test evaluation.
6. Freeze schema before test evaluation.
7. Freeze prediction parser before test evaluation.
8. Run test evaluation once with frozen configuration.
9. Do not patch evaluator after seeing test results.
10. Do not add normalization rules after seeing test results.
11. Record all hashes and command lines.
12. Publish logs needed to reproduce aggregate metrics.

## 14. Forbidden Behaviors

The following behaviors are prohibited.

### Gold / Dataset Manipulation

* gold repair during evaluation;
* gold schema repair during evaluation;
* correcting gold event types;
* correcting gold roles;
* removing difficult gold records;
* changing test split membership;
* modifying schema after test inspection.

### Prediction Repair

* schema guessing;
* role guessing;
* event type guessing;
* value completion;
* unit completion;
* company suffix completion;
* automatic alias expansion;
* automatic coreference resolution;
* automatic splitting of multi-value strings;
* converting malformed text into valid records using heuristics not frozen on dev.

### Silent Error Handling

* silent invalid role drop;
* silent invalid event type drop;
* silent invalid JSON drop;
* silent duplicate removal;
* silent value type coercion;
* silent conversion of numbers to strings;
* silent conversion of objects to strings.

All such cases must be logged and counted according to this protocol.

### Metric Contamination

* LLM judge in the main metric;
* semantic equivalence in the main metric;
* embedding similarity in the main metric;
* edit-distance matching in the main metric;
* fuzzy matching in the main metric;
* external KB normalization in the main metric;
* aggressive normalization in the main metric;
* test-set-driven normalization updates;
* post-test evaluator patching;
* replacing official metrics with unified metrics in historical comparison;
* mixing offline DuEE-Fin reproduction scores with online hidden-test leaderboard scores.

### Reporting Violations

* reporting only Unified Strict F1 while claiming historical SOTA;
* reporting only official metric while claiming cross-dataset unified evaluation;
* omitting invalid output rates for generative systems;
* hiding parser failures;
* omitting evaluator commit hash;
* omitting schema hash;
* omitting split version;
* omitting whether DuEE-Fin score is online official or offline official-style.

## 15. Final Freeze Statement

This protocol is frozen as the final evaluation specification for DuEE-Fin, ChFinAnn, and DocFEE experiments. Future changes to schema adapters, normalization rules, matching behavior, invalid-output handling, or TP/FP/FN accounting must create a new protocol version and must not be mixed with results produced under this version. Dataset-official metrics remain mandatory for historical comparability, while Unified Strict Role-Value Micro-F1 is the frozen main scientific metric for cross-dataset evaluation. Test results are valid only when produced with frozen code, frozen configuration, recorded hashes, and no post-test evaluator modification.
