"""Product database — stores product knowledge for Customer Support mode."""

import sqlite3
import json
import os

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "products.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    return sqlite3.connect(_DB_PATH)


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                brand       TEXT NOT NULL,
                name        TEXT NOT NULL,
                model       TEXT NOT NULL UNIQUE,
                category    TEXT,
                price       TEXT,
                warranty    TEXT,
                description TEXT,
                features    TEXT,   -- JSON array of strings
                in_the_box  TEXT,   -- JSON array of strings
                specs       TEXT    -- JSON object
            );

            CREATE TABLE IF NOT EXISTS product_issues (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL,
                issue       TEXT NOT NULL,
                symptoms    TEXT,
                solution    TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS product_faqs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL,
                question    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)
    _seed()


# ── Seed data ─────────────────────────────────────────────────────────────────

def _seed_product_1(c: sqlite3.Connection) -> None:
    """Shark Detect Pet Pro LA450UKT — skip if already present."""
    if c.execute("SELECT 1 FROM products WHERE model='LA450UKT'").fetchone():
        return

    c.execute("""
        INSERT INTO products (brand, name, model, category, price, warranty, description, features, in_the_box, specs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SharkNinja",
        "Shark Detect Pet Pro Corded Upright Vacuum",
        "LA450UKT",
        "Upright Vacuum Cleaner",
        "£329.99",
        "5-Year Limited Warranty",
        (
            "The Shark Detect Pet Pro is a powerful corded upright vacuum designed for homes with pets. "
            "Its Anti Hair Wrap Plus technology uses specially engineered bristles with a chevron pattern "
            "that pulls dirt, debris, and hair to the centre of the brush-roll, where anti-wrap combs "
            "actively remove it as you clean. Smart Detect sensors adjust performance automatically."
        ),
        json.dumps([
            "Anti Hair Wrap Plus technology — chevron bristles guide hair to anti-wrap combs",
            "Smart Detect sensors — automatically adjusts suction to surface type",
            "Pet-optimized design — deep cleans carpets and hard floors with pet hair",
            "Large capacity dustbin — fewer trips to empty",
            "Extended power cord — longer reach than standard models",
            "Washable filter — rinse and reuse, no replacement needed",
            "Multiple attachments included — crevice tool, upholstery tool, pet tool",
            "5-year limited warranty for peace of mind",
        ]),
        json.dumps([
            "Shark Detect Pet Pro Upright Vacuum (main unit)",
            "Crevice tool",
            "Upholstery tool",
            "Pet multi-tool",
            "Dusting brush",
        ]),
        json.dumps({
            "type": "Corded Upright",
            "colour": "Grey",
            "rating": "4.2 / 5 (109 reviews)",
            "recommend_rate": "78% of reviewers recommend",
            "suitable_for": "Pet hair, carpets, hard floors",
            "avg_scores": {"value": 4.4, "performance": 4.6, "quality": 4.0, "design": 3.9},
        }),
    ))

    pid = c.execute("SELECT id FROM products WHERE model='LA450UKT'").fetchone()[0]

    c.executemany(
        "INSERT INTO product_issues (product_id, issue, symptoms, solution) VALUES (?, ?, ?, ?)",
        [(pid, i, s, sol) for i, s, sol in [
            (
                "Loss of suction",
                "Vacuum not picking up debris, weak airflow, reduced cleaning power",
                (
                    "1. Switch off and unplug the vacuum before checking anything. "
                    "2. Empty the dustbin — suction drops significantly when it's full. "
                    "3. Check and clean the foam and felt filters: remove them, tap out dust over a bin, "
                    "then rinse under cold water. Allow to air-dry for at least 24 hours before reinserting — never put wet filters back in. "
                    "4. Check the hose and attachments for blockages — detach them and look through for any clogs. "
                    "5. Check the brush-roll area for tangled hair or debris. "
                    "If suction is still weak after all these steps, contact SharkNinja support under your 5-year warranty."
                ),
            ),
            (
                "Brush roll not spinning",
                "Brush roll has stopped rotating, carpet not being agitated, red indicator light",
                (
                    "1. Switch off and unplug immediately. "
                    "2. Turn the vacuum over and inspect the brush-roll for tangled hair, string, or debris. "
                    "3. Even with Anti Hair Wrap Plus, very thick tangles can occasionally jam the roll — "
                    "use scissors to carefully cut and remove any wrapped material. "
                    "4. Check the brush-roll is properly seated in its housing — remove and re-insert if needed. "
                    "5. Press the brush-roll reset button (if present) after clearing the blockage. "
                    "6. Plug back in and test on a hard floor first. "
                    "If the brush-roll still won't spin, the motor or belt may need service — contact SharkNinja support."
                ),
            ),
            (
                "Stiff or difficult power cord",
                "Cord is rigid, hard to wrap up, gets in the way during cleaning",
                (
                    "This is a known characteristic of the LA450UKT's cord — it is stiffer than previous Shark models. "
                    "1. Before cleaning, unwind the full cord and lay it out loosely — this reduces resistance while vacuuming. "
                    "2. Use the cord wrap holder at the base of the machine (not the top) for better management. "
                    "3. Warm the cord slightly in a warm room before wrapping — cold makes it stiffer. "
                    "4. Wrap loosely in large loops rather than tight coils to reduce memory in the cord. "
                    "If the cord is causing a safety issue (fraying, damage), stop using immediately and contact support."
                ),
            ),
            (
                "Attachment or accessory not fitting / cracked",
                "Tools hard to click in, attachment won't stay on, plastic cracked when inserting",
                (
                    "1. Do not force attachments — apply firm, straight pressure aligned with the port; angling while pushing causes stress on the plastic. "
                    "2. Check the port and attachment for any visible debris that may be blocking a clean connection. "
                    "3. If the attachment has already cracked, stop using it immediately — a cracked tool can break off during use. "
                    "4. SharkNinja's 5-year warranty covers manufacturing defects including poorly designed fittings. "
                    "Contact SharkNinja support at https://support.sharkninja.co.uk/contact-us — they have been reported to replace faulty parts quickly. "
                    "5. Spare and replacement attachments can also be ordered from the SharkNinja parts store."
                ),
            ),
            (
                "Vacuum making unusual noise",
                "Loud rattling, high-pitched whine, grinding sound",
                (
                    "1. Switch off and unplug immediately. "
                    "2. Check the dustbin — a large piece of debris (coin, stone, clip) inside can rattle loudly. Empty and inspect. "
                    "3. Check the brush-roll for hard objects tangled in the bristles. "
                    "4. Check all attachments are securely connected — a loose attachment vibrates and rattles. "
                    "5. Check the filter is properly seated — a dislodged filter causes a high-pitched whistle. "
                    "6. If grinding continues after these checks, the motor or internal components may need service. "
                    "Contact SharkNinja support — covered under the 5-year warranty."
                ),
            ),
            (
                "Vacuum not turning on",
                "No power, no lights, nothing happens when switched on",
                (
                    "1. Check the power cord is fully plugged into the wall socket and the socket is switched on. "
                    "2. Try a different wall socket to rule out a tripped circuit. "
                    "3. Check the power cord for any visible damage — if damaged, stop use immediately. "
                    "4. Make sure the dustbin is correctly inserted — some Shark models have a safety cutoff when the bin is not fully seated. "
                    "5. Check the brush-roll isn't jammed (jams can trigger a thermal cutoff) — let the vacuum cool for 30 minutes then retry. "
                    "If still no power, the unit needs service. Contact SharkNinja support — covered under the 5-year warranty."
                ),
            ),
            (
                "Hair still wrapping around brush roll",
                "Hair tangling on brush despite Anti Hair Wrap Plus feature",
                (
                    "Anti Hair Wrap Plus significantly reduces wrapping but may not eliminate it entirely with very long or thick hair. "
                    "1. Switch off and unplug before inspecting the brush-roll. "
                    "2. Check the anti-wrap combs at the base of the brush-roll — if clogged with debris, clean them with a dry cloth or soft brush. "
                    "3. Use scissors to carefully remove any remaining wrapped hair. "
                    "4. Clean the brush-roll area after each use if you have long-haired pets or people in the household. "
                    "5. Run the vacuum at a slightly slower pace over heavily hair-covered areas — this gives the combs more time to work."
                ),
            ),
            (
                "Filter needs cleaning",
                "Reduced suction, musty smell, filter indicator light on",
                (
                    "The LA450UKT has a washable filter — no need to buy replacements. "
                    "1. Switch off and unplug the vacuum. "
                    "2. Locate the foam and felt filters (usually behind the dustbin). "
                    "3. Remove both filters and tap them gently over a bin to remove loose dust. "
                    "4. Rinse both filters under cold running water until the water runs clear. Do NOT use soap or put in the dishwasher. "
                    "5. Gently squeeze out excess water — do not wring. "
                    "6. Leave to air-dry completely for at least 24 hours in a warm room. "
                    "7. Only reinsert when completely dry — a damp filter damages the motor. "
                    "SharkNinja recommends cleaning the filter once a month under normal use."
                ),
            ),
        ]],
    )

    c.executemany(
        "INSERT INTO product_faqs (product_id, question, answer) VALUES (?, ?, ?)",
        [(pid, q, a) for q, a in [
            (
                "Is the Shark Detect Pet Pro good for pet hair?",
                "Yes — it is specifically designed for homes with pets. The Anti Hair Wrap Plus technology with chevron bristles and anti-wrap combs actively prevents hair from tangling on the brush-roll while cleaning. It performs well on both carpets and hard floors with pet hair.",
            ),
            (
                "How long is the power cord?",
                "The LA450UKT has a longer-than-average power cord for extended reach. The cord is reported to be stiffer than previous Shark models — unwind it fully before use for best results.",
            ),
            (
                "Does it work on hard floors and carpet?",
                "Yes — the Smart Detect sensors automatically adjust suction and brush settings for different floor types, including carpets and hard floors.",
            ),
            (
                "What is the warranty?",
                "The Shark Detect Pet Pro LA450UKT comes with a 5-Year Limited Warranty. This covers manufacturing defects. For warranty claims, contact SharkNinja support at https://support.sharkninja.co.uk/contact-us — past customers report fast service and quick part replacements.",
            ),
            (
                "How do I contact SharkNinja support?",
                "You can reach SharkNinja UK support at https://support.sharkninja.co.uk/contact-us — they handle warranty claims, replacement parts, and general support queries.",
            ),
            (
                "Can I get replacement parts or accessories?",
                "Yes — spare parts and accessories for the LA450UKT can be ordered directly from the SharkNinja website. This includes replacement filters, attachments, and brush-rolls.",
            ),
        ]],
    )
    print("[ProductDB] Seeded: Shark Detect Pet Pro LA450UKT")


def _seed_product_2(c: sqlite3.Connection) -> None:
    """Ninja CRISPi PRO 7-in-1 XL Glass Air Fryer AS101UKCY — skip if already present."""
    if c.execute("SELECT 1 FROM products WHERE model='AS101UKCY'").fetchone():
        return

    c.execute("""
        INSERT INTO products (brand, name, model, category, price, warranty, description, features, in_the_box, specs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Ninja",
        "Ninja CRISPi PRO 7-in-1 XL Glass Air Fryer",
        "AS101UKCY",
        "Air Fryer",
        "£219.99 (was £249.99)",
        "2-Year Limited Warranty",
        (
            "The Ninja CRISPi PRO is an XL glass air fryer designed for non-toxic prepping, cooking and storing. "
            "It features an extra-large 5.7L capacity glass container for crowd-pleasing family meals, plus a "
            "smaller 2.3L container for snacks, sides and starters. All containers are PFAS-free, dishwasher-safe "
            "borosilicate glass. Offers 7 cooking functions: Max Crisp, Air Fry, Bake, Prove, Roast, Dehydrate and Re-crisp. "
            "The glass design lets you see food cooking in real time and eliminates plastic contact with hot food."
        ),
        json.dumps([
            "7 cooking functions — Max Crisp, Air Fry, Bake, Prove, Roast, Dehydrate, Re-crisp",
            "Extra-large 5.7L CleanCrisp Glass container — family-sized meals",
            "2.3L CleanCrisp Glass container — snacks, sides and starters",
            "PFAS-free borosilicate glass — non-toxic cooking and storing with lids",
            "Dishwasher-safe glass containers — easy cleaning",
            "See-through glass — watch food cook in real time",
            "Compact footprint — generous capacity without taking up excessive counter space",
            "Adjustable base — flexible cooking positions",
            "2 Crisper Plates included for crispier results",
            "Storage lids included — cook, store and serve in the same container",
        ]),
        json.dumps([
            "Ninja CRISPi PRO main unit",
            "5.7L CleanCrisp Glass container with storage lid",
            "2.3L CleanCrisp Glass container with storage lid",
            "2 × Crisper Plates",
            "Adjustable base",
        ]),
        json.dumps({
            "type": "Glass Air Fryer",
            "colour": "Cyberspace",
            "rating": "4.6 / 5 (87 reviews)",
            "recommend_rate": "92% of reviewers recommend (65/71)",
            "suitable_for": "Air frying, baking, roasting, dehydrating, proving, re-crisping",
            "avg_scores": {"value": 4.5, "performance": 4.8, "quality": 5.0, "design": 4.9},
        }),
    ))

    pid = c.execute("SELECT id FROM products WHERE model='AS101UKCY'").fetchone()[0]

    c.executemany(
        "INSERT INTO product_issues (product_id, issue, symptoms, solution) VALUES (?, ?, ?, ?)",
        [(pid, i, s, sol) for i, s, sol in [
            (
                "Food burning or overcooking",
                "Food cooks too fast, edges burn, following recipe times leads to burnt results",
                (
                    "The CRISPi PRO runs hotter than many conventional air fryers — this is a known characteristic. "
                    "1. Reduce the temperature by 10–20°C compared to recipe instructions as a starting point. "
                    "2. Check food earlier than the recipe suggests — start checking at 75% of the stated cook time. "
                    "3. Use the glass container to visually monitor cooking in real time — you can see browning through the glass without opening the lid. "
                    "4. For delicate items, use the Air Fry function at a lower temperature rather than Max Crisp. "
                    "5. Smaller or thinner items will cook significantly faster — adjust accordingly. "
                    "If food consistently burns even at reduced temperatures, contact Ninja support under your 2-year warranty."
                ),
            ),
            (
                "Hot air blast from rear vent",
                "Strong hot air coming out the back, condensation on surfaces above, items near unit getting very hot",
                (
                    "The CRISPi PRO's compact rear vent concentrates airflow — this is by design but requires correct placement. "
                    "1. Do not use the unit under kitchen cabinets or in enclosed spaces — the concentrated rear vent produces significant hot air. "
                    "2. Keep at least 20–30cm clearance behind and above the unit. "
                    "3. Place on an open countertop away from walls, appliances and wooden surfaces. "
                    "4. Condensation on surfaces near the vent is normal — wipe down after use. "
                    "5. Never leave the unit unattended in an enclosed space while in use."
                ),
            ),
            (
                "Lightweight items blowing around inside",
                "Food spinning, baking paper flying, light items moving during cooking due to fan",
                (
                    "The powerful fan at startup can displace lightweight items — this is especially noticeable with thin liners or light food. "
                    "1. Do not use lightweight baking paper or foil without weighing it down with food — the initial fan blast can flip or spin it. "
                    "2. Use parchment paper cut to fit snugly inside the crisper plate with the edges tucked under food. "
                    "3. For very light items (single slices, crackers), use the 2.3L smaller container which has less airspace. "
                    "4. Once the fan stabilises after the first few seconds, food settles and cooks normally. "
                    "5. Pre-heat the unit for 3 minutes before adding food — this reduces the initial fan surge effect."
                ),
            ),
            (
                "Glass container cracked or chipped",
                "Glass bowl cracked during use or cleaning, chip on rim or base",
                (
                    "Stop using the unit immediately if the glass is cracked — do not use a cracked glass container as it may shatter under heat. "
                    "1. Inspect the glass carefully — even a hairline crack is a safety risk under repeated heating. "
                    "2. Do not subject the glass to sudden temperature changes — do not place a hot container directly into cold water. "
                    "3. Avoid hitting the rim or base against hard surfaces when loading/unloading. "
                    "4. The glass containers are covered under the 2-year warranty for manufacturing defects. "
                    "Contact Ninja support at https://support.sharkninja.co.uk/contact-us to arrange a replacement container. "
                    "5. Replacement glass containers can also be purchased separately from the Ninja website."
                ),
            ),
            (
                "Unit not turning on or heating",
                "No power, display not lighting up, unit starts but no heat produced",
                (
                    "1. Check the power cord is securely plugged into the wall socket and the socket is switched on. "
                    "2. Try a different wall socket to rule out a tripped circuit breaker. "
                    "3. Ensure the glass container is fully and correctly seated in the unit — the CRISPi PRO has a safety interlock that prevents operation if the container is not properly inserted. "
                    "4. Check the container lid is removed — the unit should not be run with the storage lid on. "
                    "5. If the unit ran for a long period and then stopped, it may have triggered a thermal overheat cutoff — unplug, allow 30 minutes to cool, then retry. "
                    "If still no power after these steps, contact Ninja support — covered under the 2-year warranty."
                ),
            ),
            (
                "White residue or marks on glass after washing",
                "Cloudy film, white spots or streaks on glass container after dishwasher",
                (
                    "White residue is typically mineral deposit from hard water — it is not a defect and does not affect safety or performance. "
                    "1. Soak the glass container in a solution of equal parts white vinegar and water for 15–20 minutes. "
                    "2. Scrub gently with a soft non-abrasive cloth — do not use steel wool or abrasive pads. "
                    "3. Rinse thoroughly with clean water and dry immediately. "
                    "4. To prevent buildup, use a rinse-aid tablet in the dishwasher or hand wash in soft water areas. "
                    "5. The glass containers are dishwasher-safe on the top rack — avoid high-temperature dishwasher cycles which accelerate mineral deposits."
                ),
            ),
            (
                "Smoke or smell during cooking",
                "Smoke coming from unit, burning smell, food residue smell",
                (
                    "1. Switch off and unplug the unit immediately if smoke is visible. "
                    "2. After the unit cools, remove and thoroughly clean the glass containers, crisper plates and adjustable base — "
                    "fat and food residue from previous cooks will smoke when heated again. "
                    "3. Clean the interior of the unit housing with a damp cloth — avoid getting moisture in the heating element area. "
                    "4. When cooking high-fat foods (bacon, sausages), some smoking is normal — ensure the unit is well-ventilated. "
                    "5. A slight smell on first use is normal as the unit burns off factory residue — run it empty at 180°C for 10 minutes before first food use. "
                    "If smoke persists after cleaning, contact Ninja support."
                ),
            ),
            (
                "Error code or display issue",
                "Error message on display, display flickering, buttons unresponsive",
                (
                    "1. Note the exact error code displayed — take a photo if possible for reference when contacting support. "
                    "2. Switch off and unplug the unit. Wait 60 seconds, then plug back in and retry. "
                    "3. Ensure the glass container is fully seated — a partially inserted container can trigger sensor errors. "
                    "4. Check for moisture around the control panel — wipe dry with a cloth if present. "
                    "5. If the display is flickering or buttons are unresponsive after a power cycle, the control board may need service. "
                    "Contact Ninja support at https://support.sharkninja.co.uk/contact-us — covered under the 2-year warranty."
                ),
            ),
        ]],
    )

    c.executemany(
        "INSERT INTO product_faqs (product_id, question, answer) VALUES (?, ?, ?)",
        [(pid, q, a) for q, a in [
            (
                "Are the glass containers safe and non-toxic?",
                "Yes — the CRISPi PRO uses PFAS-free borosilicate glass containers. There is no plastic contact with hot food. The glass is also dishwasher-safe, making cleaning easy and hygienic.",
            ),
            (
                "What are the 7 cooking functions?",
                "The Ninja CRISPi PRO offers: Max Crisp (highest heat for ultra-crispy results), Air Fry (everyday air frying), Bake, Prove (low heat for bread/dough proving), Roast, Dehydrate (low and slow for dried fruits, jerky etc.), and Re-crisp (revives leftovers to crispy again).",
            ),
            (
                "Can I use both containers at the same time?",
                "The CRISPi PRO uses one container at a time — either the 5.7L large or the 2.3L small. The two containers let you choose the right size for what you're cooking, but they are not used simultaneously.",
            ),
            (
                "What is the capacity?",
                "The Ninja CRISPi PRO AS101UKCY comes with two containers: a 5.7L large CleanCrisp Glass container (XL — suitable for whole chickens, large joints, family portions) and a 2.3L small container (ideal for snacks, sides and starters).",
            ),
            (
                "Can I store food in the glass containers with the lids?",
                "Yes — both containers come with storage lids, so you can cook, cool and store food in the same container. This is one of the key design advantages of the glass containers over plastic alternatives.",
            ),
            (
                "What is the warranty?",
                "The Ninja CRISPi PRO AS101UKCY comes with a 2-Year Limited Warranty covering manufacturing defects. For warranty claims, replacements or support, contact Ninja at https://support.sharkninja.co.uk/contact-us.",
            ),
            (
                "Do I need to preheat the air fryer?",
                "Preheating is not mandatory but recommended for best results — especially for crispy foods. Preheat for 3 minutes at your desired temperature. Preheating also reduces the strong initial fan surge that can displace lightweight liners.",
            ),
            (
                "Can I use baking paper or foil inside?",
                "Yes, but use caution. Always weigh baking paper or foil down with food before starting — the powerful fan can blow lightweight liners around on startup. Cut liners to fit the crisper plate and tuck edges under food. Never block the air circulation holes in the crisper plate.",
            ),
        ]],
    )
    print("[ProductDB] Seeded: Ninja CRISPi PRO AS101UKCY")


def _seed() -> None:
    """Seed all products — each product checks its own model before inserting."""
    with _conn() as c:
        _seed_product_1(c)
        _seed_product_2(c)


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_all_products() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, brand, name, model, category, price, warranty FROM products").fetchall()
    return [{"id": r[0], "brand": r[1], "name": r[2], "model": r[3],
             "category": r[4], "price": r[5], "warranty": r[6]} for r in rows]


def get_product_full(product_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            return None
        issues = c.execute(
            "SELECT issue, symptoms, solution FROM product_issues WHERE product_id=?", (product_id,)
        ).fetchall()
        faqs = c.execute(
            "SELECT question, answer FROM product_faqs WHERE product_id=?", (product_id,)
        ).fetchall()

    return {
        "id": row[0], "brand": row[1], "name": row[2], "model": row[3],
        "category": row[4], "price": row[5], "warranty": row[6],
        "description": row[7],
        "features": json.loads(row[8] or "[]"),
        "in_the_box": json.loads(row[9] or "[]"),
        "specs": json.loads(row[10] or "{}"),
        "issues": [{"issue": i[0], "symptoms": i[1], "solution": i[2]} for i in issues],
        "faqs": [{"question": f[0], "answer": f[1]} for f in faqs],
    }


def get_support_context() -> str:
    """Full product dump — kept as fallback. Prefer search_product_chunks() for normal calls."""
    with _conn() as c:
        products = c.execute("SELECT id FROM products").fetchall()

    if not products:
        return ""

    blocks = []
    for (pid,) in products:
        p = get_product_full(pid)
        if not p:
            continue

        lines = [
            f"=== PRODUCT: {p['brand']} {p['name']} (Model: {p['model']}) ===",
            f"Category : {p['category']}",
            f"Price    : {p['price']}",
            f"Warranty : {p['warranty']}",
            f"Rating   : {p['specs'].get('rating', 'N/A')}",
            "",
            "DESCRIPTION:",
            p["description"],
            "",
            "KEY FEATURES:",
        ]
        for f in p["features"]:
            lines.append(f"  • {f}")

        lines += ["", "IN THE BOX:"]
        for item in p["in_the_box"]:
            lines.append(f"  • {item}")

        lines += ["", "KNOWN ISSUES & TROUBLESHOOTING:"]
        for issue in p["issues"]:
            lines += [
                f"\n  ISSUE: {issue['issue']}",
                f"  Symptoms: {issue['symptoms']}",
                f"  Solution: {issue['solution']}",
            ]

        lines += ["", "FREQUENTLY ASKED QUESTIONS:"]
        for faq in p["faqs"]:
            lines += [
                f"\n  Q: {faq['question']}",
                f"  A: {faq['answer']}",
            ]

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


# ── Semantic search (BM25-style keyword scoring) ──────────────────────────────

_STOP_WORDS = {
    "the", "a", "an", "is", "it", "my", "i", "and", "or", "not", "to",
    "in", "for", "of", "on", "at", "with", "this", "that", "have", "has",
    "been", "be", "are", "was", "were", "do", "does", "did", "can", "will",
    "just", "but", "so", "what", "how", "why", "when", "me", "its",
}


def _tokenize(text: str) -> list[str]:
    import re
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _score(query_tokens: list[str], chunk_text: str) -> float:
    """BM25-inspired term frequency score with position bonus for title hits."""
    if not query_tokens:
        return 0.0
    text_tokens = _tokenize(chunk_text)
    if not text_tokens:
        return 0.0
    freq: dict[str, int] = {}
    for t in text_tokens:
        freq[t] = freq.get(t, 0) + 1
    k1, b = 1.5, 0.75
    avg_len = 60  # approximate average chunk length in tokens
    score = 0.0
    for qt in query_tokens:
        tf = freq.get(qt, 0)
        if tf == 0:
            # Try prefix match (e.g. "suctions" matches "suction")
            tf = sum(1 for t in freq if t.startswith(qt) or qt.startswith(t))
        if tf:
            norm_tf = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(text_tokens) / avg_len))
            score += norm_tf
    return score


def _build_chunks(p: dict) -> list[tuple[str, str]]:
    """Return (chunk_type, text) pairs for a single product."""
    header = (
        f"PRODUCT: {p['brand']} {p['name']} (Model: {p['model']})\n"
        f"Category: {p['category']}  |  Price: {p['price']}  |  Warranty: {p['warranty']}\n"
        f"Rating: {p['specs'].get('rating', 'N/A')}\n\n"
        f"DESCRIPTION: {p['description']}"
    )
    chunks = [("header", header)]

    if p["features"]:
        chunks.append(("features", "KEY FEATURES:\n" + "\n".join(f"  • {f}" for f in p["features"])))

    if p["in_the_box"]:
        chunks.append(("in_the_box", "IN THE BOX:\n" + "\n".join(f"  • {i}" for i in p["in_the_box"])))

    for issue in p["issues"]:
        text = (
            f"ISSUE: {issue['issue']}\n"
            f"Symptoms: {issue['symptoms']}\n"
            f"Solution: {issue['solution']}"
        )
        chunks.append(("issue", text))

    for faq in p["faqs"]:
        chunks.append(("faq", f"Q: {faq['question']}\nA: {faq['answer']}"))

    return chunks


def search_product_chunks(query: str, top_k: int = 5) -> str:
    """
    Return the most relevant product knowledge chunks for a customer query.
    Reduces injected context from ~8,500 chars to ~1,000–2,000 chars per call.
    """
    with _conn() as c:
        pids = [r[0] for r in c.execute("SELECT id FROM products").fetchall()]

    if not pids:
        return ""

    query_tokens = _tokenize(query)

    # Score all chunks including headers; track which header belongs to which product
    scored: list[tuple[float, str, str]] = []   # (score, chunk_type, text)
    pid_to_header: dict[int, str] = {}          # product_id → header text

    for pid in pids:
        p = get_product_full(pid)
        if not p:
            continue
        chunks = _build_chunks(p)
        for ctype, text in chunks:
            s = _score(query_tokens, text)
            scored.append((s, ctype, text))
            if ctype == "header":
                pid_to_header[pid] = text

    scored.sort(key=lambda x: x[0], reverse=True)

    # Find the product whose non-header chunks score highest — include its header first
    best_pid = None
    for score, ctype, text in scored:
        if ctype != "header" and score > 0:
            # Identify which product this chunk belongs to
            for pid in pids:
                p = get_product_full(pid)
                if p and any(text == t for _, t in _build_chunks(p)):
                    best_pid = pid
                    break
        if best_pid:
            break

    seen: set[str] = set()
    results: list[str] = []

    # Lead with the most relevant product's header
    if best_pid and best_pid in pid_to_header:
        results.append(pid_to_header[best_pid])
        seen.add(pid_to_header[best_pid])
    elif pid_to_header:
        # Fallback: first product header if no strong non-header match
        first_header = next(iter(pid_to_header.values()))
        results.append(first_header)
        seen.add(first_header)

    # Add top scored non-header chunks
    for score, ctype, text in scored:
        if len(results) >= top_k:
            break
        if ctype != "header" and text not in seen:
            results.append(text)
            seen.add(text)

    result_text = "\n\n---\n\n".join(results)
    total_chars = len(result_text)
    print(f"[ProductDB] Semantic search: {len(results)} chunks, {total_chars} chars injected (query: '{query[:60]}')")
    return result_text


def add_product(brand: str, name: str, model: str, category: str = "",
                price: str = "", warranty: str = "", description: str = "",
                features: list | None = None, in_the_box: list | None = None,
                specs: dict | None = None) -> int:
    with _conn() as c:
        c.execute(
            "INSERT INTO products (brand, name, model, category, price, warranty, description, features, in_the_box, specs) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (brand, name, model, category, price, warranty, description,
             json.dumps(features or []), json.dumps(in_the_box or []), json.dumps(specs or {})),
        )
        return c.execute("SELECT id FROM products WHERE model=?", (model,)).fetchone()[0]


def add_issue(product_id: int, issue: str, symptoms: str, solution: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO product_issues (product_id, issue, symptoms, solution) VALUES (?, ?, ?, ?)",
            (product_id, issue, symptoms, solution),
        )


def add_faq(product_id: int, question: str, answer: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO product_faqs (product_id, question, answer) VALUES (?, ?, ?)",
            (product_id, question, answer),
        )
