## Architecture decisions

### 1. Discount tiers are percentage-only, not absolute prices

RG Faserverbund publishes staffels as "from N units, 5%". Modelling
them as percentages keeps the YAML compact and makes catalog edits
trivial when a supplier nudges a list price (the percentages don't
change). Absolute-price tiers would force every list-price update to
also touch every tier, multiplying maintenance cost.

The trade-off: when a supplier eventually offers a *flat staffel
price* (e.g. "€19.95 from 5 units" instead of "−12% from 5 units"),
the percentage model is lossy. We accept that — no current supplier
ships flat-price staffels, and we can extend the model later with a
union (`BundleDiscount = PercentTier | FlatPriceTier`) without
breaking existing YAML.

### 2. Tiers are strictly ascending on both keys

A tier table like `[(2, 5%), (4, 5%)]` is meaningless — the second
tier never applies. A table like `[(4, 5%), (2, 10%)]` is a data
error: the higher-quantity tier offers less discount. Both shapes are
rejected at load time so the YAML is self-validating; the optimizer
never sees a degenerate tier table.

### 3. Tier match is "highest min_quantity ≤ count"

For tiers `[(2, 5%), (4, 10%), (8, 15%)]` and `count = 5`, the 5%
tier *and* the 10% tier both qualify; the 10% tier wins. This matches
how every supplier we surveyed renders their staffel: the highest
applicable discount is the one charged. The validator's strict-
ascending invariant ensures this is unambiguous.

### 4. Discounts apply per-package, not per-allocation

A `PurchaseLineItem` may carry allocations across multiple packages
(e.g. one 25 kg + one 5 kg). Each package's count is matched against
its *own* tier table independently; there is no "combined-units"
basket. This matches supplier behaviour: RG Faserverbund's 5 kg
staffel does not credit you for buying a 25 kg canister too.

The optimizer already enumerates `(package, count)` pairs, so applying
the discount is a one-line transformation on each candidate's cost
contribution.

### 5. Cost integers stay in cents, percentages do not introduce floats

Existing optimizer arithmetic ranks on integer cents. The discount
percentage is a `Decimal` in `(0, 1)`. Application:
`discounted_cents = (price_cents * (1 - pct)).quantize(0, ROUND_HALF_UP)`
— a single `Decimal` multiplication per candidate, then back to
integer cents. No floats, no drift, deterministic. The
display-precision boundary remains the renderer.

### 6. Schema additions are additive and optional

`product_url` defaults to `None`; `bundle_discounts` defaults to
empty. Existing project files and existing in-flight code paths see
no behaviour change until the optimizer step lands. This lets us land
the data carrier first (already done) and the optimizer wiring later
without a coordination window.

### 7. No basket-level or supplier-level aggregation in this change

Suppliers sometimes offer "free shipping over €X" or "−€10 on orders
≥ €100". Those are basket-level rules and require modelling shipping
cost, minimum-order thresholds, and order grouping. None of those
exist in the current catalog. We deliberately stop at the per-SKU
staffel level and leave basket-level discount modelling for a
separate change with its own data shape and UX.

## Risks and mitigations

- **Risk:** Catalog editor adds a tier with `min_quantity = 1` or
  `discount_pct = 0`. **Mitigation:** Pydantic validators reject both
  with clear error messages.
- **Risk:** Optimizer becomes non-deterministic because tier
  application changes the cost rank between runs. **Mitigation:** Tier
  application is a pure function of `(package, count, catalog)`; no
  randomness, no I/O, same inputs → same output. Existing determinism
  tests are extended to cover discounted catalogs.
- **Risk:** A supplier replaces a percentage tier with an absolute
  price tier and we silently apply the wrong discount.
  **Mitigation:** The price-refresh skill verifies both list price and
  staffel structure; a structural mismatch (flat-price tier on the
  page, percentage tier in YAML) surfaces as a diff for the user to
  resolve.
