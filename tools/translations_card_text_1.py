"""Card effect text, cards 0-30 (TXT-2304..TXT-2411), first pass.

The in-game card text table stores each card's lines in reverse display order.
These translations are written so the game's normal display order reads as a
coherent effect. Shared lines (e.g. "*Only S/M-types can equip.") use the same
generic wording wherever they appear.
"""

CARD_TEXT_1 = {
    # Card 0 — Death Saurer
    "TXT-2411": "(Including diagonals) around the user's square,",
    "TXT-2410": "all Zoids in the area take",
    "TXT-2409": "300 damage.",
    "TXT-2408": "*Includes base and allies.",

    # Card 1 — Iron Kong
    "TXT-2407": "Fire at a square 5-10 spaces ahead",
    "TXT-2406": "in a straight line.",
    "TXT-2405": "Zoids in the target square take",
    "TXT-2404": "and Zoids in adjacent squares take",
    "TXT-2403": "200 damage.",

    # Card 2 — Saber Tiger
    "TXT-2402": "Jump over all terrain except bases",
    "TXT-2401": "(forests, rivers, barricades) and Zoids,",
    "TXT-2400": "and move straight up to 5 spaces.",
    "TXT-2399": "*However, normal movement cannot",
    "TXT-2398": "be done in the same turn.",

    # Card 3 — Red Horn
    "TXT-2397": "Instead of counterattacking, roll a die and",
    "TXT-2396": "add the result x100",
    "TXT-2395": "points to HP.",
    "TXT-2394": "*Adding beyond max durability",
    "TXT-2393": "cannot be done.",

    # Card 4 — Redler
    "TXT-2392": "Range +2.",
    "TXT-2391": "Attack = M-type +100, L-type +200.",
    "TXT-2390": "While equipped, this unit can attack and counter",
    "TXT-2389": "only targets straight ahead.",
    "TXT-2388": "*Only M/L-types can equip. Water/air types",
    "TXT-2387": "cannot equip it.",
    "TXT-2386": "*To make a normal attack or counterattack, discard",
    "TXT-2385": "this card.",

    # Card 5 — Brachios
    "TXT-2384": "When attacking, attack the same enemy twice in a row.",
    "TXT-2383": "This can be done.",
    "TXT-2382": "*Only S-types can equip.",
    "TXT-2381": "*After two attacks, you receive one counterattack.",

    # Card 6 — Morga
    "TXT-2380": "Damage from enemy attacks",
    "TXT-2379": "is reduced by 100.",

    # Card 7 — Iguan
    "TXT-2378": "HP +300, straight movement +1.",
    "TXT-2377": "*When this card is trashed,",
    "TXT-2376": "300 HP is also lost.",

    # Cards 8-11
    "TXT-2375": "Attack +200.",
    "TXT-2374": "Attack +100.",
    "TXT-2373": "Range +1.",
    "TXT-2372": "Can also attack and counter diagonally backward (1 space).",

    # Card 12 — Rev Raptor
    "TXT-2371": "Even units without mountain aptitude can move through",
    "TXT-2370": "mountains and forests at a movement cost of 1.",
    "TXT-2369": "*Only S/M-types can equip.",

    # Card 13 — Gator
    "TXT-2368": "Even units without water aptitude can move through water.",
    "TXT-2367": "*Saboteur cannot",
    "TXT-2366": "discard this card.",

    # Card 14 — Saber Tiger RS
    "TXT-2365": "Movement +2.",
    "TXT-2364": "*Only M/L-types can equip.",

    # Card 15 — Iron Kong SS
    "TXT-2363": "is reduced by 200.",

    # Card 16 — Death Saurer V1
    "TXT-2362": "Enemy hit chance decreases.",
    "TXT-2361": "When making a hit check, subtract 1 from the die roll",
    "TXT-2360": "and check the result.",

    # Card 17 — Gustav MS
    "TXT-2359": "Move one of your Zoids 6 spaces.",
    "TXT-2358": "This movement is not affected by terrain.",
    "TXT-2357": "*Terrain movement restrictions do not apply.",

    # Card 18 — Iron Kong PK
    "TXT-2356": "Move one enemy Zoid 6 spaces.",
    "TXT-2355": "You can do this.",
    "TXT-2354": "*Terrain movement restrictions still apply.",
    "TXT-2353": "*Determine the Zoid's facing after moving.",
    "TXT-2352": "Can be done.",

    # Card 19 — Saber Tiger SS
    "TXT-2351": "From your discard pile, return one Custom Card",
    "TXT-2350": "to your hand.",

    # Card 20 — Geno Breaker
    "TXT-2349": "When your Zoid attacks, its attack power is",
    "TXT-2348": "increased by 200.",
    "TXT-2347": "*Only one attack is affected.",
    "TXT-2346": "Attack +200.",

    # Card 21 — Black Rhimos
    "TXT-2345": "Self-destruct one of your Zoids. Its HP becomes 0,",
    "TXT-2344": "and all Zoids within 2 squares (including diagonals)",
    "TXT-2343": "take damage.",
    "TXT-2342": "Damage by distance:",
    "TXT-2341": "1st square: 300 damage",
    "TXT-2340": "2nd square: 200 damage",
    "TXT-2339": "*Includes base and allies.",

    # Card 22 — Redler BC
    "TXT-2338": "Look at the opponent's hand and make them discard",
    "TXT-2337": "one card of your choice.",
    "TXT-2336": "You can do this.",

    # Card 23 — Thinker
    "TXT-2335": "Choose one of your Zoids with 300 HP or less",
    "TXT-2334": "and discard one Custom Card to recover HP.",
    "TXT-2333": "HP can be recovered by discarding.",
    "TXT-2332": "*Excludes bases.",
    "TXT-2331": "*Cannot exceed maximum durability.",

    # Card 24 — Geno Breaker RS
    "TXT-2330": "Discard one Custom Card equipped to an enemy Zoid.",
    "TXT-2329": "You can discard one.",

    # Card 25 — Death Stinger K
    "TXT-2328": "Draw 3 new cards.",
    "TXT-2327": "*Can only be used on your own turn.",

    # Card 26 — Lightning Saix K
    "TXT-2326": "Up to two of your Zoids each",
    "TXT-2325": "gain HP.",

    # Card 27 — Thinker K
    "TXT-2323": "Place one barricade chip on any empty square.",
    "TXT-2322": "You can place one barricade chip. Barricade chips",
    "TXT-2321": "cannot be entered or passed through.",
    "TXT-2320": "*Excludes flying types.",
    "TXT-2319": "*Cannot be placed on water squares.",

    # Card 28 — Saber Tiger AT
    "TXT-2318": "Remove one barricade chip from the map.",
    "TXT-2317": "You can remove one.",

    # Card 29 — Saber Tiger FT
    "TXT-2316": "[Piercing] Declare before attacking.",
    "TXT-2315": "Two Zoids within the front range",
    "TXT-2314": "take 500 damage.",
    "TXT-2313": "*If a 1 is rolled on the die, HP -300.",
    "TXT-2312": "*Only M-types can equip.",
    "TXT-2311": "*<Guard> is nullified.",

    # Card 30 — Geno Saurer K
    "TXT-2310": "Declare before attacking.",
    "TXT-2309": "Hit chance is -1, but the Zoid hit",
    "TXT-2308": "is immediately paralyzed.",
    "TXT-2307": "<Paralyzed> That Zoid cannot attack or counterattack",
    "TXT-2306": "either.",
    "TXT-2305": "*Returns to normal on the next turn.",
    "TXT-2304": "*Only S/M-type Zoids can equip.",
}
