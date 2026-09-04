# All-Country Current FCV Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing bounded current-context stage work consistently for every recognized country, favor trusted news, UN, humanitarian, and FCV think-tank reporting, and fail honestly to document-led review when no qualifying recent source is established.

**Architecture:** Keep the existing research controller. Harden its country-agnostic provider search with API-enforced domains and grounded publication dates, then run the deterministic recovery gateway using a dynamic ReliefWeb query and optional checked-in ICG feeds. Reuse COUNTRY_ALIASES, CurrentContextClaim, existing source validation, sufficiency, prompts, and smoke runner; add no dependency and no new service or adapter abstraction.

**Tech Stack:** Python 3.13, Pydantic, stdlib URL/date/XML handling, existing httpx client, pytest, Playwright smoke runner, Flask smoke mode.

---

## File map

- Modify src/cpf_fcv_reviewer/country_detection.py: add the missing FY2027 territories and expose the existing canonicalizer.
- Modify src/cpf_fcv_reviewer/public_research.py: enforce provider domains, ground publication dates without page_age, distinguish an optional ReliefWeb distributor, and retain the source-policy boundary.
- Modify src/cpf_fcv_reviewer/curated_research.py: canonicalize country queries, use ReliefWeb original dates and originating publishers, and expand the static official ICG feed catalogue.
- Modify src/cpf_fcv_reviewer/research_controller.py: preserve one-source reduced behavior while generic indicator data cannot produce a current-evidence tier.
- Modify prompts/public_research.md and prompts/review.md: make FCV relevance, date, and citation-fit rules explicit without adding a model call.
- Modify focused tests in tests/test_country_detection.py, tests/test_public_research.py, tests/test_curated_research.py, tests/test_research_controller.py, tests/test_adversarial.py, and the existing runner-contract test.
- Add docs/validation/2026-09-05-all-country-current-fcv-provider-free.md only after the gates pass.
- Update docs/PROJECT_STATUS.md with verified aggregate results and explicit remaining gates.

Create a new implementation branch from updated main; keep PR #8 as the design record:

~~~powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c fix/all-country-current-fcv-research
~~~

Expected: a clean feature branch based on the commit containing the merged design. Do not deploy or invoke an assessment, provider-backed research gateway, or assistant endpoint during Tasks 1-7.

### Task 1: Cover every FY2027 FCV/fragility country through the existing country registry

**Files:**
- Modify: tests/test_country_detection.py
- Modify: src/cpf_fcv_reviewer/country_detection.py:28-241

- [ ] **Step 1: Write the failing FY2027 coverage and alias tests**

Add these constants and tests:

~~~python
FY27_PUBLIC_FCV = {
    "Afghanistan", "Burkina Faso", "Cameroon", "Central African Republic",
    "Democratic Republic of the Congo", "Ethiopia", "Haiti", "Iran", "Iraq",
    "Lebanon", "Libya", "Mali", "Mozambique", "Myanmar", "Niger", "Nigeria",
    "Papua New Guinea", "Somalia", "South Sudan", "Sudan", "Syria", "Ukraine",
    "West Bank and Gaza", "Yemen",
}

FY27_INSTITUTIONAL_FRAGILITY = {
    "Afghanistan", "Central African Republic", "Chad", "Comoros", "Congo",
    "Eritrea", "Guinea-Bissau", "Haiti", "Kiribati", "Malawi", "Maldives",
    "Marshall Islands", "Micronesia", "Mozambique", "Myanmar", "Papua New Guinea",
    "Sao Tome and Principe", "Solomon Islands", "Somalia", "South Sudan", "Sudan",
    "Syria", "Timor-Leste", "Tuvalu", "Yemen",
}

def test_country_registry_covers_current_fy27_fcv_and_fragility_lists():
    for name in FY27_PUBLIC_FCV | FY27_INSTITUTIONAL_FRAGILITY:
        assert canonical_country(name) in COUNTRY_ALIASES


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("DRC", "Democratic Republic of the Congo"),
        ("Congo, Rep.", "Congo"),
        ("West Bank and Gaza (territory)", "West Bank and Gaza"),
        ("Palestine", "West Bank and Gaza"),
        ("Türkiye", "Türkiye"),
        ("Côte d'Ivoire", "Cote d'Ivoire"),
        ("São Tomé and Príncipe", "Sao Tomé and Príncipe"),
        ("Kosovo", "Kosovo"),
    ],
)
def test_research_country_aliases_are_canonical(alias, expected):
    assert canonical_country(alias) == expected
~~~

Import COUNTRY_ALIASES and canonical_country from the module. The FY2027 sets are test evidence, not production classifications; generated reviews must not infer or state FCV status from them.

- [ ] **Step 2: Run the tests and confirm the missing coverage**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_country_detection.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-country-red"
~~~

Expected: FAIL because canonical_country is not public and West Bank and Gaza/Kosovo are absent.

- [ ] **Step 3: Make the smallest registry change**

Add these entries alphabetically:

~~~python
"Kosovo": (),
"West Bank and Gaza": (
    "West Bank and Gaza (territory)",
    "Palestine",
    "Palestinian Territories",
),
~~~

Extend the existing aliases with Congo, Rep.; Congo, Dem. Rep.; Iran, Islamic Rep.; Micronesia, Fed. Sts.; and Yemen, Rep. Export existing behavior without duplicating it:

~~~python
def canonical_country(value: str) -> str | None:
    return _canonical_country(value)
~~~

- [ ] **Step 4: Run the focused tests**

Run Step 2 again. Expected: all country-detection tests PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add -- src/cpf_fcv_reviewer/country_detection.py tests/test_country_detection.py
git diff --cached --check
git commit -m "fix: cover current FCV country aliases"
~~~

### Task 2: Enforce trusted provider domains and verified publication dates

**Files:**
- Modify: tests/test_public_research.py
- Modify: src/cpf_fcv_reviewer/public_research.py:190-318,461-746
- Modify: prompts/public_research.md

- [ ] **Step 1: Write failing domain and date-provenance tests**

Use the existing fake clients to capture the web-search tool dictionary, then assert:

~~~python
tool = captured["tools"][0]
assert tool["allowed_domains"] == list(public_research.TRUSTED_SEARCH_DOMAINS)
assert {
    "reuters.com", "apnews.com", "bbc.com", "unhcr.org", "iom.int",
    "wfp.org", "undp.org", "crisisgroup.org", "issafrica.org",
} <= set(tool["allowed_domains"])
~~~

Add the date regressions:

~~~python
def test_page_age_never_becomes_publication_date():
    title, url, publication_date = public_research._source_metadata({
        "title": "Guinea update",
        "url": "https://www.reuters.com/world/africa/guinea-update",
        "page_age": "2026-08-30",
    })
    assert title == "Guinea update"
    assert url == "https://www.reuters.com/world/africa/guinea-update"
    assert publication_date is None


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"published_at": "2026-08-30"}, date(2026, 8, 30)),
        ({"cited_text": "Published August 30, 2026."}, date(2026, 8, 30)),
        ({"url": "https://www.reuters.com/world/africa/update/2026-08-30/"}, date(2026, 8, 30)),
    ],
)
def test_only_permitted_grounded_date_bases_are_accepted(item, expected):
    assert public_research._grounded_publication_date(item) == expected
~~~

- [ ] **Step 2: Verify red**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_public_research.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-public-red"
~~~

Expected: FAIL because allowed_domains is absent and page_age is promoted.

- [ ] **Step 3: Derive one provider domain tuple from the existing allowlist**

After _INSTITUTIONAL_PUBLISHER_HOSTS add:

~~~python
TRUSTED_SEARCH_DOMAINS = tuple(
    sorted({
        host
        for hosts, _publisher in _INSTITUTIONAL_PUBLISHER_HOSTS.values()
        for host in hosts
    })
)
~~~

This prevents provider-side and post-response policy drift.

- [ ] **Step 4: Add the tuple to the existing web-search tool**

~~~python
{
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
    "allowed_domains": list(TRUSTED_SEARCH_DOMAINS),
}
~~~

Do not increase max_uses or add another request.

- [ ] **Step 5: Replace page_age dating with three explicit bases**

Beside _parse_source_date add:

~~~python
_LABELED_DATE = re.compile(
    r"\b(?:published|publication date|dated)\s*:?[ \t]+"
    r"(?P<date>\d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d{1,2}, \d{4})\b",
    re.IGNORECASE,
)
_URL_DATE = re.compile(r"/(\d{4})[-/](\d{2})[-/](\d{2})(?:/|$)")


def _grounded_publication_date(item: object) -> date | None:
    for field in ("published_at", "published_date", "publication_date", "date"):
        parsed = _parse_source_date(_value(item, field))
        if parsed is not None:
            return parsed
    cited_text = _as_nonblank_string(_value(item, "cited_text"))
    if cited_text:
        match = _LABELED_DATE.search(cited_text)
        if match:
            parsed = _parse_source_date(match.group("date"))
            if parsed is not None:
                return parsed
    url = _normalize_source_url(_value(item, "url"))
    match = _URL_DATE.search(urlparse(url).path) if url else None
    if match:
        try:
            return date(*(int(part) for part in match.groups()))
        except ValueError:
            return None
    return None
~~~

Make _source_metadata call this helper. While processing citation blocks, merge the citation date into the already grounded result before attaching it. Preserve exact canonical URL/title matching and fail closed when no verified date exists.

- [ ] **Step 6: Tighten the existing prompt without expanding scope**

Append:

~~~text
Search only the configured trusted domains. Prioritize recent country-specific reporting on political or governance transition, conflict or violence, displacement or humanitarian conditions, peace and security, land or resource conflict, social cohesion, and material implementation or resilience risks. Do not use page age, retrieval date, or an inferred date as publication evidence. Generic GDP, population, life-expectancy, poverty, or similar indicators are background data and are not current FCV evidence.
~~~

- [ ] **Step 7: Run tests and commit**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_public_research.py tests/test_adversarial.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-public-green"
git add -- src/cpf_fcv_reviewer/public_research.py prompts/public_research.md tests/test_public_research.py
git diff --cached --check
git commit -m "fix: constrain and date current FCV search"
~~~

Expected: focused tests PASS and the diff check is silent.

### Task 3: Attribute ReliefWeb reports to their originating publisher and original date

**Files:**
- Modify: tests/test_public_research.py
- Modify: tests/test_curated_research.py
- Modify: src/cpf_fcv_reviewer/public_research.py:23-55,190-318,672-744
- Modify: src/cpf_fcv_reviewer/curated_research.py:328-384,624-656,750-779

- [ ] **Step 1: Write failing provenance tests**

Change the success fixture:

~~~python
"date": {
    "original": "2026-07-28T00:00:00+00:00",
    "created": "2026-08-01T00:00:00+00:00",
},
"source": [{"name": "UN OCHA"}],
~~~

Assert:

~~~python
assert claim.publisher == "OCHA"
assert claim.distributor == "ReliefWeb"
assert claim.source_date == date(2026, 7, 28)
~~~

Add tests proving creation-only rows and unknown source organizations are rejected. Add a normalization test proving a model claim cannot invent distributor metadata:

~~~python
source = public_research.ResearchSource(
    title="Report",
    url="https://reliefweb.int/report/example",
    published_at=date(2026, 8, 1),
)
claim = _claim(
    publisher="OCHA", source_url=source.url, source_date=source.published_at
).model_copy(update={"distributor": "ReliefWeb"})
retained = public_research._validate_normalized_claims(
    (claim,), public_research.SearchArtifact(narrative="Grounded.", sources=(source,))
)
assert retained == ()
~~~

- [ ] **Step 2: Verify red**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_curated_research.py tests/test_public_research.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-reliefweb-red"
~~~

Expected: FAIL because claims have no distributor, use date.created, and name ReliefWeb as publisher.

- [ ] **Step 3: Add one optional provenance field**

In CurrentContextClaim add the backwards-compatible default:

~~~python
distributor: Literal["ReliefWeb"] | None = None
~~~

Add "un ocha" as an OCHA alias in _INSTITUTIONAL_PUBLISHER_HOSTS and add:

~~~python
def canonical_institutional_publisher(value: str) -> str | None:
    entry = _INSTITUTIONAL_PUBLISHER_HOSTS.get(_normalize_text(value))
    return entry[1] if entry is not None else None
~~~

In _is_permitted_public_source, keep normal direct-host validation first, then add the narrow curated exception:

~~~python
if allowed_hosts and _host_matches(source_url, allowed_hosts):
    return True
return bool(
    claim.distributor == "ReliefWeb"
    and _host_matches(source_url, ("reliefweb.int",))
    and canonical_institutional_publisher(claim.publisher) == claim.publisher
)
~~~

In _validate_normalized_claims and _salvage_grounded_segments force distributor=None. Provider normalization cannot create this application-owned exception.

- [ ] **Step 4: Query and parse the original date**

Canonicalize with canonical_country(request.country); return an empty tuple for an unrecognized value. Change ReliefWeb request fields:

~~~python
("filter[conditions][1][field]", "date.original"),
("fields[include][]", "date.original"),
("fields[include][]", "date.created"),
("sort[]", "date.original:desc"),
~~~

Replace _reliefweb_date:

~~~python
def _reliefweb_original_date(value: object) -> date | None:
    if not isinstance(value, Mapping):
        return None
    raw = value.get("original")
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
~~~

In _reliefweb_claim canonicalize source.name. Reject unknown sources and ReliefWeb-as-origin, then build:

~~~python
publisher = canonical_institutional_publisher(source_name)
if publisher is None or publisher == "ReliefWeb":
    return None

return CurrentContextClaim(
    claim_id=f"reliefweb:{digest}",
    text=f"{title}.",
    publisher=publisher,
    source_title=title,
    source_url=source_url,
    distributor="ReliefWeb",
    source_date=source_date,
    source_type="institutional public report",
    relevance=f"ReliefWeb report attributed to {publisher}.",
    context_kind="current_development",
    relationship="establishes",
    licensed_data_required=False,
)
~~~

- [ ] **Step 5: Preserve deterministic ordering**

Add claim.distributor or "" to _claim_stable_key immediately after source_url.

- [ ] **Step 6: Run tests and commit**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_public_research.py tests/test_curated_research.py tests/test_research_controller.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-reliefweb-green"
git add -- src/cpf_fcv_reviewer/public_research.py src/cpf_fcv_reviewer/curated_research.py tests/test_public_research.py tests/test_curated_research.py tests/test_research_controller.py
git diff --cached --check
git commit -m "fix: preserve ReliefWeb source provenance"
~~~

Expected: PASS; diversity counts use originating organizations.

### Task 4: Replace the Guinea-only ICG map with an audited optional catalogue

**Files:**
- Modify: tests/test_curated_research.py
- Modify: src/cpf_fcv_reviewer/curated_research.py:26,287-325

- [ ] **Step 1: Write failing catalogue tests**

~~~python
@pytest.mark.parametrize(
    "country",
    [
        "Afghanistan", "Burkina Faso", "Central African Republic",
        "Democratic Republic of the Congo", "Guinea", "Haiti", "Iran", "Iraq",
        "Lebanon", "Libya", "Mali", "Myanmar", "Nigeria", "Somalia", "South Sudan",
        "Sudan", "Syria", "Ukraine", "West Bank and Gaza", "Yemen",
    ],
)
def test_icg_catalogue_has_official_feed_for_supported_conflict_country(country):
    feed = curated_research._CRISIS_GROUP_FEEDS[country]
    assert re.fullmatch(r"https://www\.crisisgroup\.org/rss/\d+", feed)
~~~

Also assert Kiribati returns empty without a request. Retain malformed XML, stale item, unsafe URL, response-size, and timeout tests.

- [ ] **Step 2: Verify red**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_curated_research.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-icg-red"
~~~

Expected: FAIL except Guinea.

- [ ] **Step 3: Check in the official FY2027-relevant catalogue**

Replace the lowercase map with these official RSS-index values verified 2026-09-05:

~~~python
_CRISIS_GROUP_FEEDS = {
    "Afghanistan": "https://www.crisisgroup.org/rss/36",
    "Burkina Faso": "https://www.crisisgroup.org/rss/21",
    "Burundi": "https://www.crisisgroup.org/rss/3",
    "Cameroon": "https://www.crisisgroup.org/rss/4",
    "Central African Republic": "https://www.crisisgroup.org/rss/5",
    "Chad": "https://www.crisisgroup.org/rss/6",
    "Comoros": "https://www.crisisgroup.org/rss/174",
    "Congo": "https://www.crisisgroup.org/rss/115",
    "Democratic Republic of the Congo": "https://www.crisisgroup.org/rss/7",
    "Eritrea": "https://www.crisisgroup.org/rss/10",
    "Ethiopia": "https://www.crisisgroup.org/rss/116",
    "Guinea": "https://www.crisisgroup.org/rss/23",
    "Guinea-Bissau": "https://www.crisisgroup.org/rss/24",
    "Haiti": "https://www.crisisgroup.org/rss/80",
    "Iran": "https://www.crisisgroup.org/rss/85",
    "Iraq": "https://www.crisisgroup.org/rss/87",
    "Lebanon": "https://www.crisisgroup.org/rss/82",
    "Libya": "https://www.crisisgroup.org/rss/95",
    "Malawi": "https://www.crisisgroup.org/rss/161",
    "Maldives": "https://www.crisisgroup.org/rss/160",
    "Mali": "https://www.crisisgroup.org/rss/26",
    "Mozambique": "https://www.crisisgroup.org/rss/118",
    "Myanmar": "https://www.crisisgroup.org/rss/45",
    "Niger": "https://www.crisisgroup.org/rss/27",
    "Nigeria": "https://www.crisisgroup.org/rss/28",
    "Papua New Guinea": "https://www.crisisgroup.org/rss/126",
    "Sao Tomé and Príncipe": "https://www.crisisgroup.org/rss/154",
    "Solomon Islands": "https://www.crisisgroup.org/rss/152",
    "Somalia": "https://www.crisisgroup.org/rss/12",
    "South Sudan": "https://www.crisisgroup.org/rss/13",
    "Sudan": "https://www.crisisgroup.org/rss/14",
    "Syria": "https://www.crisisgroup.org/rss/83",
    "Timor-Leste": "https://www.crisisgroup.org/rss/49",
    "Ukraine": "https://www.crisisgroup.org/rss/72",
    "West Bank and Gaza": "https://www.crisisgroup.org/rss/91",
    "Yemen": "https://www.crisisgroup.org/rss/90",
}
~~~

Use canonical_country once in supports/search and exact canonical keys. Do not scrape at assessment time.

- [ ] **Step 4: Run tests and commit**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_country_detection.py tests/test_curated_research.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-icg-green"
git add -- src/cpf_fcv_reviewer/curated_research.py tests/test_curated_research.py
git diff --cached --check
git commit -m "feat: expand official ICG country feeds"
~~~

### Task 5: Make one relevant source sufficient and generic indicators insufficient

**Files:**
- Modify: tests/test_public_research.py
- Modify: tests/test_research_controller.py
- Modify: tests/test_adversarial.py
- Modify: src/cpf_fcv_reviewer/public_research.py:87-116
- Modify: prompts/review.md:120-132,185-196

- [ ] **Step 1: Change the generic-indicator regression to document-led**

~~~python
def test_generic_indicator_recovery_alone_is_document_led():
    indicator = claim("indicator").model_copy(
        update={
            "source_type": "institutional public data",
            "source_title": "Population, total",
            "text": "Population, total: 14,754,785.",
            "relevance": "World Bank indicator observation.",
        }
    )
    result = controller(
        ScriptedGateway(((),)),
        recovery_gateway=ScriptedRecoveryGateway((indicator,)),
        max_attempts=1,
    ).run(holistic_request(), lambda *_: None, allow_document_led=True)
    assert result.tier is CurrentEvidenceTier.DOCUMENT_LED
    assert result.claims == ()
~~~

Keep the one-report case but use publisher OCHA, distributor ReliefWeb, and tier REDUCED. Add a two-URL/one-publisher limitation assertion and assert the wording does not call URLs institutional sources.

- [ ] **Step 2: Add prompt regressions**

~~~python
def test_review_prompt_rejects_generic_indicators_as_current_fcv_proof():
    prompt = load_review_prompt()
    assert "GDP, population, life expectancy, poverty" in prompt
    assert "must not substantiate political transition, violence, displacement, land conflict" in prompt
    assert "direct or indirect FCV causal pathway" in prompt
    assert "more materially FCV-related priorities first" in prompt
~~~

- [ ] **Step 3: Verify red**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_research_controller.py tests/test_public_research.py tests/test_adversarial.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-tier-red"
~~~

Expected: the indicator is retained/reduced or prompt assertions fail.

- [ ] **Step 4: Reject only the known generic-data class at the common boundary**

~~~python
def _is_generic_indicator_data(claim: CurrentContextClaim) -> bool:
    return _normalize_text(claim.source_type) == "institutional public data"
~~~

In retain_public_claims before permitted-source validation:

~~~python
elif _is_generic_indicator_data(claim):
    rejected[claim.claim_id] = "generic indicator data is not current FCV evidence"
~~~

This removes generic indicators from sufficiency and recommendation evidence without rejecting analytical World Bank FCV reports. No thematic classifier or score is needed. The controller's existing allow_document_led and not accepted branch then works unchanged.

- [ ] **Step 5: Strengthen the review prompt in place**

~~~text
GDP, population, life expectancy, poverty, and other generic indicators are background context only. They must not substantiate political transition, violence, displacement, land conflict, social cohesion, or similar present-day dynamics. Cite a current-context item only when its title and claim materially support the recommendation's specific present-day assertion. Every priority must state a direct or indirect FCV causal pathway, and more materially FCV-related priorities must appear first.
~~~

- [ ] **Step 6: Run tests and commit**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_public_research.py tests/test_research_controller.py tests/test_adversarial.py tests/test_validators.py tests/test_prompt_guardrails.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-tier-green"
git add -- src/cpf_fcv_reviewer/public_research.py prompts/review.md tests/test_public_research.py tests/test_research_controller.py tests/test_adversarial.py
git diff --cached --check
git commit -m "fix: require substantive current FCV evidence"
~~~

Expected: one relevant report yields reduced; generic indicator-only input yields document_led; pathway/order tests PASS.

### Task 6: Keep the external runner title mode-tolerant

**Files:**
- Modify: the existing runner-contract test found with rg
- Modify only if needed: scripts/run_smoke_browser.py

- [ ] **Step 1: Locate and test the existing assertion**

~~~powershell
rg -n "Guinea CPF|Guinea CEN|FCV review" tests scripts/run_smoke_browser.py
~~~

The contract must accept:

~~~python
assert_title("Guinea CPF / CEN FCV review")
assert_title("Guinea CPF FCV review")
assert_title("Guinea CEN FCV review")
with pytest.raises(AssertionError):
    assert_title("Guinea project review")
~~~

The implementation may use:

~~~python
re.compile(r"^Guinea (?:CPF|CEN|CPF / CEN) FCV review$")
~~~

If current main already fully covers this, make no code change and no commit.

- [ ] **Step 2: Run the exact existing contract file**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_external_qa_runner.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-runner-title"
~~~

If rg shows a different file name, run that file instead. Expected: PASS.

- [ ] **Step 3: Commit only if coverage was missing**

~~~powershell
git add -- scripts/run_smoke_browser.py tests
git diff --cached --check
git commit -m "test: allow mode-controlled review titles"
~~~

### Task 7: Run the complete provider-free acceptance ladder

**Files:**
- No production changes expected.
- Smoke artifacts remain under gitignored output/playwright.

- [ ] **Step 1: Run the focused matrix**

~~~powershell
C:\WBG\Python313\python.exe -m pytest tests/test_country_detection.py tests/test_public_research.py tests/test_curated_research.py tests/test_research_controller.py tests/test_adversarial.py tests/test_prompt_guardrails.py tests/test_validators.py -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-all-country-focused"
~~~

Expected: PASS, zero provider calls.

- [ ] **Step 2: Run static checks**

~~~powershell
C:\WBG\Python313\python.exe -m compileall -q src tests scripts
node --check src/cpf_fcv_reviewer/static/app.js
git diff --check origin/main...HEAD
~~~

Expected: exit 0. If Ruff is already available in .venv, run .\.venv\Scripts\python.exe -m ruff check .; otherwise record unavailable and do not install it.

- [ ] **Step 3: Run the full provider-free suite once**

~~~powershell
C:\WBG\Python313\python.exe -m pytest -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\cpf-fcv-all-country-full"
~~~

Expected: PASS. Do not repeat a green full suite without a code change.

- [ ] **Step 4: Run the complete external smoke-browser runner**

Start the documented local smoke server, then:

~~~powershell
C:\WBG\Python313\python.exe scripts/run_smoke_browser.py --base-url http://127.0.0.1:5000 --output-dir output/playwright/2026-09-05-all-country-current-fcv-smoke
~~~

Expected:

~~~text
BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1
~~~

Verify upload, result, detailed view, two assistant turns, four restored messages after refresh, 390-pixel mobile layout, DOCX, and zero console/page errors. Stop the server. These are synthetic artifacts, not a country-quality run.

- [ ] **Step 5: Inspect the narrow diff**

~~~powershell
git status --short --branch
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- src/cpf_fcv_reviewer prompts tests scripts docs
~~~

Expected: only planned files; no secrets, raw documents, raw model output, assessment IDs, run-state files, or unrelated changes.

### Task 8: Record safe evidence and stop at the operational gate

**Files:**
- Create: docs/validation/2026-09-05-all-country-current-fcv-provider-free.md
- Modify: docs/PROJECT_STATUS.md

- [ ] **Step 1: Write the record from observed output**

Use this structure. Convert the two instruction phrases in the Results list into the exact observed values before creating the record:

~~~markdown
# All-country current FCV research provider-free validation - 2026-09-05

## Scope

This provider-free cycle validates country-agnostic trusted-domain search configuration,
grounded publication-date handling, dynamic ReliefWeb parsing, official optional ICG feed
selection, substantive current-FCV sufficiency, publisher diversity, and the complete smoke
browser workflow. No assessment or provider-backed assistant call was made.

## Results

- Focused country/research suite: copy the exact passed count printed by Task 7, Step 1.
- Complete provider-free suite: copy the exact passed count printed by Task 7, Step 3.
- Python compilation, JavaScript syntax, and diff checks: passed.
- External smoke runner: BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1.
- Verified code commit: copy the full output of git rev-parse HEAD after the code commits.

## Operational gate

ReliefWeb production readiness remains blocked until a genuinely pre-approved application
name is configured and a single no-model API probe succeeds. No deployment and no paid
assessment were performed. No assessment identifier is recorded.
~~~

Do not invent counts or SHA. If a gate fails, record the failure.

- [ ] **Step 2: Update status narrowly**

Record the verified result and these remaining actions:

~~~text
- Obtain/configure a genuinely pre-approved ReliefWeb application name.
- Run bounded live no-model ReliefWeb probes for a conflict country, an institutionally fragile country, and a valid zero-result country.
- Present the diff, provider-free evidence, and probe results for explicit deployment/paid-run approval.
~~~

Do not claim production readiness while the approved app name is missing.

- [ ] **Step 3: Commit documentation**

~~~powershell
git add -- docs/PROJECT_STATUS.md docs/validation/2026-09-05-all-country-current-fcv-provider-free.md
git diff --cached --check
git commit -m "docs: record all-country provider-free validation"
~~~

- [ ] **Step 4: Request review, then push and open the implementation PR**

Use superpowers:requesting-code-review and resolve evidence-backed findings. Push the implementation branch and open a PR. The PR body must state no deployment, no paid assessment, no provider-backed assistant call, the open ReliefWeb app-name gate, focused/full/smoke results, and no assessment ID.

- [ ] **Step 5: Stop before deployment or paid validation**

Do not deploy, submit an assessment, call the production assistant, or treat arbitrary ReliefWeb app names as valid. Present provider-free evidence and request explicit approval only after the approved ReliefWeb credential and no-model probes are available.

## Plan self-review

- Spec coverage: Tasks 1-5 cover country normalization, trusted domains, grounded dates, ReliefWeb provenance, ICG supplements, one-source reduced tier, indicator exclusion, citation fit, pathways, and ordering. Tasks 6-8 cover runner compatibility, full provider-free validation, safe records, and deployment/paid gates.
- Simplicity: no new dependency, commercial API, runtime feed scraping, thematic classifier, adapter abstraction, extra model call, or production FCV classification logic.
- Type consistency: CurrentContextClaim.distributor is optional with None default; only trusted ReliefWeb adapter output sets it. Existing constructors remain valid. Country and publisher canonicalization are shared.
- Operational limitation: fixture implementation can complete, but ReliefWeb production readiness cannot pass until an approved app name exists. This is an explicit stop condition, not a reason to weaken validation.
