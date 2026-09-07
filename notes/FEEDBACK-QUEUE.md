# Feedback queue — raised while reading, not yet done

TJ reads the generated pages and gives feedback faster than it can be acted on. Losing an
item because it arrived mid-task is the failure this file exists to prevent. Anything here
is **agreed and not yet built**; when it ships it moves to the bottom with the commit that
did it.

Nothing in this file is a claim about the data. It is a work list.

---

## Open

### 1. A fund name on the right-hand side does not read as a use of money

*Raised 7 Sept 2026, on `school-money-flow.html` and `town-money-flow.html`.*

The right column is meant to answer **what the money was spent on**. Where we cannot see
that, it currently falls back to naming the fund — so the right-hand box says
`After school fund`, which reads as a place money sits rather than a thing money bought.
TJ: *"putting a 'fund' on the right is awkward. I can't understand how to read it."*

**The pattern to apply instead:** when the spending breakdown is unknown, the right-hand
box takes the **left box's title minus the fund number**, plus the word **spent**.

    left:  2200 School Lunch Revolving      ->  right:  School Lunch Revolving spent
    left:  1311 School Gift Fund            ->  right:  School Gift Fund spent

Why it is the right call and not just a rename: the current label quietly implies we know
the destination when all we know is the total that left the fund. The new label says
exactly what was measured — money left this fund — and nothing more. That is rule 7 in a
box title.

Watch for: the fund-number prefix is not always the same shape (`2200`, `1301`, `1311`),
so strip a leading number by pattern rather than by a fixed width, and assert that
stripping changed something for every box it is applied to — a silent no-op would leave
the old confusing label in place and nothing would fail.

---

## Done

*(nothing yet)*
