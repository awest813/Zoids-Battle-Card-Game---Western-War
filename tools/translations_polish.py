"""Short story lines and pointer-specific translations for the English text tables."""

from translations_memory import MEMORY_SLOT_TEXT

POLISH = {
    "TXT-0616": "order and discipline to Europa.",
    "TXT-0617": "It's our duty to bring",
    "TXT-0638": "Our Empire advanced, and from the east",
    "TXT-0677": "Only the Command Wolf is a threat.",
    "TXT-0700": "It is a key point overlooking the area.",
    "TXT-0701": "That place is key to Europa.",
    "TXT-0740": "Enemy base activity has stopped.",
    "TXT-0770": "A Twin Rapid-Fire Cannon? We'll take it.",
    "TXT-0795": "Same unit as Lt. Col. Schwarz",
    "TXT-0807": "Your Excellency, reinforcements are here.",
    "TXT-0815": "The enemy relies on quality over quantity.",
    "TXT-0849": "There is still time before the operation.",
    "TXT-0855": "Reports say Grey Last has weapons",
    "TXT-0856": "According to the captured pilot",
    "TXT-0862": "The Zoid that arrived needs adjustment",
    "TXT-0903": "Now's our chance while it's being serviced.",
    "TXT-0920": "Assemble in South Europa by sea.",
    "TXT-0942": "Used well, it could be a fine weapon.",
    "TXT-0950": "They approached underwater, so detection was",
    "TXT-0963": "In time for the South Europa operation",
    "TXT-1000": "Nothing should trouble Your Excellency.",
    "TXT-1038": "There's still time before the operation.",
    "TXT-1050": "Reached the Ubas Mountains' east coast.",
    "TXT-1089": "The search found the Zoid and the girl",
    "TXT-1118": "We could not have done it without you.",
    "TXT-1137": "Sorry, but I need you to run a drill.",
    "TXT-1142": "But there truly isn't much time.",
    "TXT-1281": "I am Lt. Col. Schwarz of the Imperial Army.",
    "TXT-1290": "You two will defend the new base.",
    "TXT-1294": "A base at South Europa's northern tip.",
    "TXT-1307": "Keep them away from the new base!",
    "TXT-1347": "Good, the North Europa base is",
    "TXT-1368": "We'll attack from the mountain side.",
    "TXT-1393": "Our final destination is the Bront Plain.",
    "TXT-1399": "Enemy communications reveal the facility's",
    "TXT-1410": "If we strike, it must be now.",
    "TXT-1425": "Even Gojulas can't take a particle cannon.",
    "TXT-1447": "To counter the enemy particle cannon",
    "TXT-1451": "Better to destroy the base early.",
    "TXT-1473": "Reinforcements from Nix as well.",
    "TXT-1482": "Send the Imperials northwest of West Europa.",
    "TXT-1536": "Imperial Zoids closing from four sides.",
    "TXT-1551": "Little time remains before the operation.",
    "TXT-1560": "Deployment preparations aren't complete,",
    "TXT-1577": "With the units from the northern route",
}

# Some Japanese endings complete different English sentences at each script pointer.
STORY_SLOT_ENDINGS = {
    "TXT-0478": {
        0x800C5BF4: "around a leader.",
        0x800CB2D4: "from home.",
    },
    "TXT-0695": {
        0x800C9C2C: "in the desert they fled to.",
        0x800CE868: "on Mount Olympus.",
    },
    "TXT-0816": {
        0x800CA868: "Landing again will be hard.",
        0x800CA8B4: "wisely now.",
        0x800CD90C: "for now.",
        0x800CE0F8: "Zoids anymore.",
        0x800CFD98: "our last battle here.",
    },
    "TXT-0960": {
        0x800CB8C8: "from home.",
        0x800CC17C: "from Gaigalus.",
        0x800CC3AC: "from Gaigalus.",
        0x800CEE14: "it just arrived.",
    },
    "TXT-1013": {
        0x800CBF7C: "soon.",
        0x800CC4B8: "survey the ruins.",
        0x800CC694: "soon. Time is short.",
    },
    "TXT-1341": {
        0x800CE2EC: "on the Rob Plain.",
        0x800CF250: "to West Europa.",
    },
}

SLOT_TRANSLATIONS = MEMORY_SLOT_TEXT | STORY_SLOT_ENDINGS
